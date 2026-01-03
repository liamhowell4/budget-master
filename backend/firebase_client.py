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

from .output_schemas import Expense, ExpenseType, Date, RecurringExpense, PendingExpense, FrequencyType

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

    def get_expense_by_id(self, expense_id: str) -> Optional[Dict]:
        """
        Get a single expense by its document ID.

        Args:
            expense_id: Firestore document ID

        Returns:
            Expense dict with 'id' field, or None if not found
        """
        doc_ref = self.db.collection("expenses").document(expense_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        expense_data = doc.to_dict()
        expense_data["id"] = doc.id
        return expense_data

    def update_expense(
        self,
        expense_id: str,
        expense_name: Optional[str] = None,
        amount: Optional[float] = None,
        date: Optional[Date] = None,
        category: Optional[ExpenseType] = None
    ) -> bool:
        """
        Update an expense's fields (partial update).

        Args:
            expense_id: Firestore document ID
            expense_name: New expense name (optional)
            amount: New amount (optional)
            date: New date (optional)
            category: New category (optional)

        Returns:
            True if updated, False if expense not found
        """
        doc_ref = self.db.collection("expenses").document(expense_id)

        # Check if expense exists
        if not doc_ref.get().exists:
            return False

        # Build update dict (only include provided fields)
        updates = {}
        if expense_name is not None:
            updates["expense_name"] = expense_name
        if amount is not None:
            updates["amount"] = amount
        if date is not None:
            updates["date"] = {
                "day": date.day,
                "month": date.month,
                "year": date.year
            }
        if category is not None:
            updates["category"] = category.name

        # Perform update (keep original timestamp)
        if updates:
            doc_ref.update(updates)

        return True

    def delete_expense(self, expense_id: str) -> bool:
        """
        Delete an expense by its document ID.

        Args:
            expense_id: Firestore document ID

        Returns:
            True if deleted, False if expense not found
        """
        doc_ref = self.db.collection("expenses").document(expense_id)

        # Check if expense exists
        if not doc_ref.get().exists:
            return False

        doc_ref.delete()
        return True

    def get_recent_expenses_from_db(
        self,
        limit: int = 20,
        category: Optional[ExpenseType] = None,
        days_back: int = 7
    ) -> List[Dict]:
        """
        Get recent expenses (last N days or limit, whichever is fewer).

        Args:
            limit: Maximum number of expenses to return (default 20)
            category: Optional category filter
            days_back: Number of days to look back (default 7)

        Returns:
            List of expense dicts sorted by most recent first
        """
        from datetime import datetime, timedelta
        import pytz

        # Calculate date range (last N days in user's timezone)
        user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)
        start_date = now - timedelta(days=days_back)

        # Build query
        query = self.db.collection("expenses")
        query = query.where(filter=FieldFilter("timestamp", ">=", start_date))

        if category:
            query = query.where(filter=FieldFilter("category", "==", category.name))

        # Order by most recent first and limit
        query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)

        # Execute query
        docs = query.stream()

        expenses = []
        for doc in docs:
            expense_data = doc.to_dict()
            expense_data["id"] = doc.id
            expenses.append(expense_data)

        return expenses

    def search_expenses_in_db(
        self,
        text_query: str,
        category: Optional[ExpenseType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Search expenses by name (substring match).

        Note: Firestore doesn't support full-text search natively,
        so we fetch all expenses in the date range and filter in Python.

        Args:
            text_query: Search string (case-insensitive substring match)
            category: Optional category filter
            start_date: Optional start date (defaults to first day of current month)
            end_date: Optional end date (defaults to today)

        Returns:
            List of matching expense dicts
        """
        from datetime import datetime
        import pytz

        # Default to current month if no date range specified
        if not start_date or not end_date:
            user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
            tz = pytz.timezone(user_timezone)
            now = datetime.now(tz)

            if not start_date:
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if not end_date:
                end_date = now

        # Get expenses in date range
        expenses = self.get_expenses(start_date, end_date, category)

        # Filter by text query (case-insensitive substring match)
        query_lower = text_query.lower()
        results = [
            exp for exp in expenses
            if query_lower in exp.get("expense_name", "").lower()
        ]

        return results

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

    def get_warned_thresholds(self, year: int, month: int) -> List[int]:
        """
        Get list of overall budget thresholds already warned about for a given month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            List of threshold percentages already warned about (e.g., [50, 90])
        """
        doc_id = f"{year}-{month:02d}"
        doc = self.db.collection("budget_alert_tracking").document(doc_id).get()

        if doc.exists:
            data = doc.to_dict()
            return data.get("thresholds_warned", [])

        return []

    def add_warned_threshold(self, year: int, month: int, threshold: int) -> None:
        """
        Add a threshold to the list of warned thresholds for a given month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            threshold: Threshold percentage (50, 90, 95, or 100)
        """
        doc_id = f"{year}-{month:02d}"
        doc_ref = self.db.collection("budget_alert_tracking").document(doc_id)

        # Get existing thresholds
        existing_doc = doc_ref.get()
        if existing_doc.exists:
            existing_thresholds = existing_doc.to_dict().get("thresholds_warned", [])
        else:
            existing_thresholds = []

        # Add new threshold if not already present
        if threshold not in existing_thresholds:
            existing_thresholds.append(threshold)
            existing_thresholds.sort()  # Keep sorted for readability

            doc_ref.set({
                "thresholds_warned": existing_thresholds,
                "last_updated": firestore.SERVER_TIMESTAMP
            })

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

    # ==================== Recurring Expense Operations ====================

    def save_recurring_expense(self, recurring: RecurringExpense) -> str:
        """
        Save a recurring expense template to Firestore.

        Args:
            recurring: RecurringExpense object

        Returns:
            Document ID of the saved recurring expense
        """
        recurring_data = {
            "expense_name": recurring.expense_name,
            "amount": recurring.amount,
            "category": recurring.category.name,
            "frequency": recurring.frequency.value,
            "day_of_month": recurring.day_of_month,
            "day_of_week": recurring.day_of_week,
            "last_of_month": recurring.last_of_month,
            "last_reminded": {
                "day": recurring.last_reminded.day,
                "month": recurring.last_reminded.month,
                "year": recurring.last_reminded.year
            } if recurring.last_reminded else None,
            "last_user_action": {
                "day": recurring.last_user_action.day,
                "month": recurring.last_user_action.month,
                "year": recurring.last_user_action.year
            } if recurring.last_user_action else None,
            "active": recurring.active,
            "created_at": firestore.SERVER_TIMESTAMP
        }

        # Add to Firestore
        doc_ref = self.db.collection("recurring_expenses").add(recurring_data)
        return doc_ref[1].id

    def get_recurring_expense(self, template_id: str) -> Optional[RecurringExpense]:
        """
        Get a specific recurring expense by ID.

        Args:
            template_id: Document ID

        Returns:
            RecurringExpense object or None
        """
        doc = self.db.collection("recurring_expenses").document(template_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        return self._dict_to_recurring_expense(data, template_id)

    def get_all_recurring_expenses(self, active_only: bool = True) -> List[RecurringExpense]:
        """
        Get all recurring expense templates.

        Args:
            active_only: If True, only return active recurring expenses

        Returns:
            List of RecurringExpense objects
        """
        query = self.db.collection("recurring_expenses")

        if active_only:
            query = query.where(filter=FieldFilter("active", "==", True))

        docs = query.stream()

        recurring_expenses = []
        for doc in docs:
            data = doc.to_dict()
            recurring = self._dict_to_recurring_expense(data, doc.id)
            recurring_expenses.append(recurring)

        return recurring_expenses

    def update_recurring_expense(self, template_id: str, updates: Dict) -> None:
        """
        Update a recurring expense template.

        Args:
            template_id: Document ID
            updates: Dictionary of fields to update
        """
        self.db.collection("recurring_expenses").document(template_id).update(updates)

    def delete_recurring_expense(self, template_id: str) -> None:
        """
        Delete a recurring expense template (or mark as inactive).

        Args:
            template_id: Document ID
        """
        # Mark as inactive instead of deleting
        self.db.collection("recurring_expenses").document(template_id).update({"active": False})

    def _dict_to_recurring_expense(self, data: Dict, template_id: str) -> RecurringExpense:
        """Convert Firestore dict to RecurringExpense object."""
        # Parse category
        category_str = data.get("category", "OTHER")
        try:
            category = ExpenseType[category_str]
        except KeyError:
            category = ExpenseType.OTHER

        # Parse frequency
        freq_str = data.get("frequency", "monthly")
        try:
            frequency = FrequencyType[freq_str.upper()]
        except KeyError:
            frequency = FrequencyType.MONTHLY

        # Parse dates
        last_reminded = None
        if data.get("last_reminded"):
            lr = data["last_reminded"]
            last_reminded = Date(day=lr["day"], month=lr["month"], year=lr["year"])

        last_user_action = None
        if data.get("last_user_action"):
            lua = data["last_user_action"]
            last_user_action = Date(day=lua["day"], month=lua["month"], year=lua["year"])

        return RecurringExpense(
            template_id=template_id,
            expense_name=data.get("expense_name", ""),
            amount=data.get("amount", 0),
            category=category,
            frequency=frequency,
            day_of_month=data.get("day_of_month"),
            day_of_week=data.get("day_of_week"),
            last_of_month=data.get("last_of_month", False),
            last_reminded=last_reminded,
            last_user_action=last_user_action,
            active=data.get("active", True)
        )

    # ==================== Pending Expense Operations ====================

    def save_pending_expense(self, pending: PendingExpense) -> str:
        """
        Save a pending expense to Firestore.

        Args:
            pending: PendingExpense object

        Returns:
            Document ID of the saved pending expense
        """
        pending_data = {
            "template_id": pending.template_id,
            "expense_name": pending.expense_name,
            "amount": pending.amount,
            "date": {
                "day": pending.date.day,
                "month": pending.date.month,
                "year": pending.date.year
            },
            "category": pending.category.name,
            "sms_sent": pending.sms_sent,
            "awaiting_confirmation": pending.awaiting_confirmation,
            "created_at": firestore.SERVER_TIMESTAMP
        }

        # Add to Firestore
        doc_ref = self.db.collection("pending_expenses").add(pending_data)
        return doc_ref[1].id

    def get_pending_expense(self, pending_id: str) -> Optional[PendingExpense]:
        """
        Get a specific pending expense by ID.

        Args:
            pending_id: Document ID

        Returns:
            PendingExpense object or None
        """
        doc = self.db.collection("pending_expenses").document(pending_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        return self._dict_to_pending_expense(data, pending_id)

    def get_all_pending_expenses(self, awaiting_only: bool = True) -> List[Dict]:
        """
        Get all pending expenses.

        Args:
            awaiting_only: If True, only return pending expenses awaiting confirmation

        Returns:
            List of dictionaries with pending expense data + pending_id
        """
        query = self.db.collection("pending_expenses")

        if awaiting_only:
            query = query.where(filter=FieldFilter("awaiting_confirmation", "==", True))

        docs = query.stream()

        pending_expenses = []
        for doc in docs:
            data = doc.to_dict()
            data["pending_id"] = doc.id
            pending_expenses.append(data)

        return pending_expenses

    def get_pending_by_template(self, template_id: str) -> Optional[Dict]:
        """
        Get pending expense for a specific recurring template.

        Args:
            template_id: Recurring expense template ID

        Returns:
            Pending expense dict or None
        """
        query = self.db.collection("pending_expenses").where(
            filter=FieldFilter("template_id", "==", template_id)
        ).where(
            filter=FieldFilter("awaiting_confirmation", "==", True)
        ).limit(1)

        docs = list(query.stream())

        if docs:
            data = docs[0].to_dict()
            data["pending_id"] = docs[0].id
            return data

        return None

    def update_pending_expense(self, pending_id: str, updates: Dict) -> None:
        """
        Update a pending expense.

        Args:
            pending_id: Document ID
            updates: Dictionary of fields to update
        """
        self.db.collection("pending_expenses").document(pending_id).update(updates)

    def delete_pending_expense(self, pending_id: str) -> None:
        """
        Delete a pending expense.

        Args:
            pending_id: Document ID
        """
        self.db.collection("pending_expenses").document(pending_id).delete()

    def _dict_to_pending_expense(self, data: Dict, pending_id: str) -> PendingExpense:
        """Convert Firestore dict to PendingExpense object."""
        # Parse category
        category_str = data.get("category", "OTHER")
        try:
            category = ExpenseType[category_str]
        except KeyError:
            category = ExpenseType.OTHER

        # Parse date
        date_data = data.get("date", {})
        expense_date = Date(
            day=date_data.get("day", 1),
            month=date_data.get("month", 1),
            year=date_data.get("year", 2025)
        )

        return PendingExpense(
            pending_id=pending_id,
            template_id=data.get("template_id", ""),
            expense_name=data.get("expense_name", ""),
            amount=data.get("amount", 0),
            date=expense_date,
            category=category,
            sms_sent=data.get("sms_sent", False),
            awaiting_confirmation=data.get("awaiting_confirmation", True)
        )
