"""
Firebase Client - Handles all Firestore and Firebase Storage operations.
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter

from .output_schemas import Expense, ExpenseType, Date

load_dotenv(override=True)


class FirebaseClient:
    """Handles all Firebase operations for expense tracking."""

    def __init__(self):
        """Initialize Firebase Admin SDK."""
        # Check if already initialized
        if not firebase_admin._apps:
            firebase_key = os.getenv("FIREBASE_KEY")

            if not firebase_key:
                raise ValueError("FIREBASE_KEY environment variable not set")

            # Try to parse as JSON string first, otherwise treat as file path
            try:
                key_dict = json.loads(firebase_key)
                cred = credentials.Certificate(key_dict)
            except json.JSONDecodeError:
                # Assume it's a file path
                cred = credentials.Certificate(firebase_key)

            firebase_admin.initialize_app(cred, {
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', '')
            })

        self.db = firestore.client()
        self.bucket = storage.bucket() if os.getenv('FIREBASE_STORAGE_BUCKET') else None

    # ==================== Expense Operations ====================

    def save_expense(self, expense: Expense, input_type: str = "text") -> str:
        """
        Save an expense to Firestore.

        Args:
            expense: The Expense object to save
            input_type: Type of input ("sms", "voice", "image", "text")

        Returns:
            Document ID of the saved expense
        """
        expense_data = {
            "expense_name": expense.expense_name,
            "amount": expense.amount,
            "date": {
                "day": expense.date.day,
                "month": expense.date.month,
                "year": expense.date.year
            },
            "category": expense.category.name,  # Store enum key
            "timestamp": firestore.SERVER_TIMESTAMP,
            "input_type": input_type
        }

        # Add to Firestore
        doc_ref = self.db.collection("expenses").add(expense_data)
        return doc_ref[1].id

    def get_expenses(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[ExpenseType] = None
    ) -> List[Dict]:
        """
        Retrieve expenses with optional filtering.

        Args:
            start_date: Filter expenses after this date
            end_date: Filter expenses before this date
            category: Filter by expense category

        Returns:
            List of expense dictionaries
        """
        query = self.db.collection("expenses")

        # Apply filters
        if start_date:
            query = query.where(filter=FieldFilter("timestamp", ">=", start_date))
        if end_date:
            query = query.where(filter=FieldFilter("timestamp", "<=", end_date))
        if category:
            query = query.where(filter=FieldFilter("category", "==", category.name))

        # Order by timestamp descending
        query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)

        # Execute query
        docs = query.stream()

        expenses = []
        for doc in docs:
            expense_data = doc.to_dict()
            expense_data["id"] = doc.id
            expenses.append(expense_data)

        return expenses

    def get_monthly_expenses(self, year: int, month: int, category: Optional[ExpenseType] = None) -> List[Dict]:
        """
        Get all expenses for a specific month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            category: Optional category filter

        Returns:
            List of expense dictionaries for the month
        """
        query = self.db.collection("expenses")

        # Filter by date fields (day, month, year)
        query = query.where(filter=FieldFilter("date.year", "==", year))
        query = query.where(filter=FieldFilter("date.month", "==", month))

        if category:
            query = query.where(filter=FieldFilter("category", "==", category.name))

        docs = query.stream()

        expenses = []
        for doc in docs:
            expense_data = doc.to_dict()
            expense_data["id"] = doc.id
            expenses.append(expense_data)

        return expenses

    def calculate_monthly_total(self, year: int, month: int, category: Optional[ExpenseType] = None) -> float:
        """
        Calculate total spending for a month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            category: Optional category filter

        Returns:
            Total amount spent
        """
        expenses = self.get_monthly_expenses(year, month, category)
        return sum(exp.get("amount", 0) for exp in expenses)

    # ==================== Budget Cap Operations ====================

    def get_budget_cap(self, category: str) -> Optional[float]:
        """
        Get budget cap for a category.

        Args:
            category: Category name (e.g., "FOOD_OUT") or "TOTAL" for overall cap

        Returns:
            Budget cap amount or None if not set
        """
        doc = self.db.collection("budget_caps").document(category).get()

        if doc.exists:
            data = doc.to_dict()
            return data.get("monthly_cap")

        return None

    def set_budget_cap(self, category: str, amount: float) -> None:
        """
        Set budget cap for a category.

        Args:
            category: Category name (e.g., "FOOD_OUT") or "TOTAL" for overall cap
            amount: Monthly budget cap amount
        """
        self.db.collection("budget_caps").document(category).set({
            "category": category,
            "monthly_cap": amount,
            "last_updated": firestore.SERVER_TIMESTAMP
        })

    def get_all_budget_caps(self) -> Dict[str, float]:
        """
        Get all budget caps.

        Returns:
            Dictionary mapping category names to budget cap amounts
        """
        docs = self.db.collection("budget_caps").stream()

        caps = {}
        for doc in docs:
            data = doc.to_dict()
            caps[data["category"]] = data["monthly_cap"]

        return caps

    # ==================== Category Operations ====================

    def get_category_data(self) -> List[Dict]:
        """
        Get all expense categories from Firestore.

        Returns:
            List of category dictionaries with id, display_value, and optional emoji
        """
        docs = self.db.collection("categories").stream()

        categories = []
        for doc in docs:
            category_data = doc.to_dict()
            category_data["id"] = doc.id
            categories.append(category_data)

        return categories

    def seed_categories(self) -> None:
        """
        Seed the categories collection from ExpenseType enum.
        This should be run once during initial setup.
        """
        # Category emoji mapping
        emoji_map = {
            "FOOD_OUT": "🍽️",
            "RENT": "🏠",
            "UTILITIES": "💡",
            "MEDICAL": "🏥",
            "GAS": "⛽",
            "GROCERIES": "🛒",
            "RIDE_SHARE": "🚕",
            "COFFEE": "☕",
            "HOTEL": "🏨",
            "TECH": "💻",
            "TRAVEL": "✈️",
            "OTHER": "📦"
        }

        for expense_type in ExpenseType:
            category_data = {
                "category_id": expense_type.name,
                "display_value": expense_type.value,
                "emoji": emoji_map.get(expense_type.name, "📦")
            }

            # Use category_id as document ID
            self.db.collection("categories").document(expense_type.name).set(category_data)

        print(f"✅ Seeded {len(ExpenseType)} categories to Firestore")

    # ==================== Firebase Storage Operations ====================

    def upload_audio(self, audio_bytes: bytes, filename: str) -> str:
        """
        Upload audio file to Firebase Storage.

        Args:
            audio_bytes: Audio file bytes
            filename: Name for the file (e.g., "recording_123.webm")

        Returns:
            Public URL of the uploaded file
        """
        if not self.bucket:
            raise ValueError("Firebase Storage bucket not configured. Set FIREBASE_STORAGE_BUCKET env var.")

        blob = self.bucket.blob(f"audio_recordings/{filename}")
        blob.upload_from_string(audio_bytes, content_type="audio/webm")

        # Make public (optional - adjust based on security needs)
        blob.make_public()

        return blob.public_url

    def get_audio_url(self, filename: str) -> str:
        """
        Get URL for an audio file in Firebase Storage.

        Args:
            filename: Name of the file

        Returns:
            Public URL
        """
        if not self.bucket:
            raise ValueError("Firebase Storage bucket not configured")

        blob = self.bucket.blob(f"audio_recordings/{filename}")
        return blob.public_url
