"""
Firebase Client - Handles all Firestore and Firebase Storage operations.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import GoogleAPIError

from .output_schemas import Expense, ExpenseType, Date, RecurringExpense, PendingExpense, FrequencyType, Category, generate_category_id
from .category_defaults import DEFAULT_CATEGORIES, MAX_CATEGORIES
from .exceptions import DocumentNotFoundError

# Load .env from project root (parent of backend/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)


class FirebaseClient:
    """Handles all Firebase operations for expense tracking."""

    # Collections that are user-scoped (stored under users/{userId}/)
    USER_SCOPED_COLLECTIONS = {
        "expenses",
        "budget_caps",
        "budget_alert_tracking",
        "recurring_expenses",
        "pending_expenses",
        "conversations",
        "categories",  # Now user-scoped for custom categories
    }

    # Collections that remain global (shared across all users)
    GLOBAL_COLLECTIONS = {"global_categories"}  # Legacy, not used for custom categories

    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize Firebase Admin SDK.

        Args:
            user_id: Optional user ID for user-scoped operations.
                     If not provided, operates on global collections (legacy mode).
        """
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
        self.user_id = user_id

    @classmethod
    def for_user(cls, user_id: str) -> "FirebaseClient":
        """
        Create a FirebaseClient scoped to a specific user.

        Args:
            user_id: Firebase Auth UID of the user

        Returns:
            FirebaseClient instance scoped to the user
        """
        return cls(user_id=user_id)

    def _get_collection_path(self, collection: str) -> str:
        """
        Get the collection path, scoped to user if applicable.

        Args:
            collection: Base collection name (e.g., "expenses")

        Returns:
            Full collection path (e.g., "users/{userId}/expenses" or "expenses")
        """
        if collection in self.GLOBAL_COLLECTIONS:
            return collection

        if self.user_id and collection in self.USER_SCOPED_COLLECTIONS:
            return f"users/{self.user_id}/{collection}"

        # Legacy mode: return global collection path
        return collection

    # ==================== Expense Operations ====================

    def save_expense(self, expense: Expense, input_type: str = "text", category_str: Optional[str] = None) -> str:
        """
        Save an expense to Firestore.

        Args:
            expense: The Expense object to save
            input_type: Type of input ("sms", "voice", "image", "text", "mcp")
            category_str: Optional category ID string override (e.g., "PET_SUPPLIES").
                          If provided, uses this instead of expense.category.name.
                          Useful for user-defined categories not in the ExpenseType enum.

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
            "category": category_str if category_str else expense.category.name,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "input_type": input_type
        }

        # Add to Firestore
        try:
            doc_ref = self.db.collection(self._get_collection_path("expenses")).add(expense_data)
            return doc_ref[1].id
        except GoogleAPIError as e:
            logger.error("Firestore write failed in save_expense: %s", e)
            raise RuntimeError(f"Failed to save expense: {e}") from e

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
        query = self.db.collection(self._get_collection_path("expenses"))

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
        query = self.db.collection(self._get_collection_path("expenses"))

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

        # Sort by timestamp descending (most recent first) for consistent ordering
        expenses.sort(key=lambda x: x.get("timestamp") or datetime.min, reverse=True)

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
        doc_ref = self.db.collection(self._get_collection_path("expenses")).document(expense_id)
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
        category: Optional[ExpenseType] = None,
        category_str: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Update an expense's fields (partial update).

        Args:
            expense_id: Firestore document ID
            expense_name: New expense name (optional)
            amount: New amount (optional)
            date: New date (optional)
            category: New category as ExpenseType (optional, for backward compat)
            category_str: New category as string (optional, for custom categories)
            timestamp: New timestamp as datetime (optional)

        Returns:
            True if updated, False if expense not found
        """
        doc_ref = self.db.collection(self._get_collection_path("expenses")).document(expense_id)

        # Check if expense exists
        if not doc_ref.get().exists:
            raise DocumentNotFoundError("expenses", expense_id)

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
        # Prefer category_str if provided (custom categories), otherwise use ExpenseType
        if category_str is not None:
            updates["category"] = category_str
        elif category is not None:
            updates["category"] = category.name
        if timestamp is not None:
            updates["timestamp"] = timestamp

        # Perform update
        if updates:
            try:
                doc_ref.update(updates)
            except GoogleAPIError as e:
                logger.error("Firestore write failed in update_expense: %s", e)
                raise RuntimeError(f"Failed to update expense: {e}") from e

        return True

    def delete_expense(self, expense_id: str) -> bool:
        """
        Delete an expense by its document ID.

        Args:
            expense_id: Firestore document ID

        Returns:
            True if deleted, False if expense not found
        """
        doc_ref = self.db.collection(self._get_collection_path("expenses")).document(expense_id)

        # Check if expense exists
        if not doc_ref.get().exists:
            raise DocumentNotFoundError("expenses", expense_id)

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
        query = self.db.collection(self._get_collection_path("expenses"))
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

    def get_expenses_in_date_range(
        self,
        start_date: Date,
        end_date: Date,
        category: Optional[ExpenseType] = None
    ) -> List[Dict]:
        """
        Get expenses within a date range using Date objects.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            category: Optional category filter

        Returns:
            List of expense dicts
        """
        query = self.db.collection(self._get_collection_path("expenses"))

        # Filter by year and month range
        # Note: This is a simplified approach - for precise filtering we'd need composite queries
        # For now, we'll fetch a wider range and filter in Python
        query = query.where(filter=FieldFilter("date.year", ">=", start_date.year))
        query = query.where(filter=FieldFilter("date.year", "<=", end_date.year))

        if category:
            query = query.where(filter=FieldFilter("category", "==", category.name))

        docs = query.stream()

        # Filter in Python for precise date matching
        expenses = []
        for doc in docs:
            expense_data = doc.to_dict()
            expense_data["id"] = doc.id

            # Parse expense date
            exp_date = expense_data.get("date", {})
            exp_year = exp_date.get("year")
            exp_month = exp_date.get("month")
            exp_day = exp_date.get("day")

            if not all([exp_year, exp_month, exp_day]):
                continue

            # Check if expense is within range
            from datetime import date as date_type
            try:
                expense_date_obj = date_type(exp_year, exp_month, exp_day)
                start_date_obj = date_type(start_date.year, start_date.month, start_date.day)
                end_date_obj = date_type(end_date.year, end_date.month, end_date.day)

                if start_date_obj <= expense_date_obj <= end_date_obj:
                    expenses.append(expense_data)
            except ValueError:
                # Invalid date, skip
                continue

        return expenses

    def get_spending_by_category(
        self,
        start_date: Date,
        end_date: Date
    ) -> Dict[str, float]:
        """
        Get spending totals grouped by category for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Dictionary mapping category names to total spending
            Example: {"FOOD_OUT": 127.50, "COFFEE": 45.00, "GROCERIES": 89.25}
        """
        expenses = self.get_expenses_in_date_range(start_date, end_date)

        # Group by category
        category_totals = {}
        for expense in expenses:
            category = expense.get("category", "OTHER")
            amount = expense.get("amount", 0)

            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += amount

        return category_totals

    def get_total_spending_for_range(
        self,
        start_date: Date,
        end_date: Date
    ) -> Dict[str, any]:
        """
        Get total spending and transaction count for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Dictionary with 'total' and 'count' keys
            Example: {"total": 456.75, "count": 23}
        """
        expenses = self.get_expenses_in_date_range(start_date, end_date)

        total = sum(exp.get("amount", 0) for exp in expenses)
        count = len(expenses)

        return {
            "total": total,
            "count": count
        }

    # ==================== Budget Cap Operations ====================

    def get_budget_cap(self, category: str) -> Optional[float]:
        """
        Get budget cap for a category.

        Args:
            category: Category name (e.g., "FOOD_OUT") or "TOTAL" for overall cap

        Returns:
            Budget cap amount or None if not set
        """
        doc = self.db.collection(self._get_collection_path("budget_caps")).document(category).get()

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
        try:
            self.db.collection(self._get_collection_path("budget_caps")).document(category).set({
                "category": category,
                "monthly_cap": amount,
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except GoogleAPIError as e:
            logger.error("Firestore write failed in set_budget_cap: %s", e)
            raise RuntimeError(f"Failed to set budget cap: {e}") from e

    def get_all_budget_caps(self) -> Dict[str, float]:
        """
        Get all budget caps.

        Returns:
            Dictionary mapping category names to budget cap amounts
        """
        docs = self.db.collection(self._get_collection_path("budget_caps")).stream()

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
        doc = self.db.collection(self._get_collection_path("budget_alert_tracking")).document(doc_id).get()

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
        doc_ref = self.db.collection(self._get_collection_path("budget_alert_tracking")).document(doc_id)

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
        Get all expense categories from Firestore (legacy method for global categories).

        Returns:
            List of category dictionaries with id, display_value, and optional emoji
        """
        docs = self.db.collection("global_categories").stream()

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
            self.db.collection("global_categories").document(expense_type.name).set(category_data)

        logger.info("Seeded %d categories to Firestore", len(ExpenseType))

    # ==================== User Custom Category Operations ====================

    def get_user_categories(self) -> List[Dict]:
        """
        Get all expense categories for the current user.

        Returns:
            List of category dictionaries sorted by sort_order
        """
        if not self.user_id:
            raise ValueError("User ID required for user-scoped categories")

        docs = self.db.collection(self._get_collection_path("categories")).stream()

        categories = []
        for doc in docs:
            category_data = doc.to_dict()
            category_data["category_id"] = doc.id
            # Ensure exclude_from_total has a default value for backwards compatibility
            if "exclude_from_total" not in category_data:
                category_data["exclude_from_total"] = False
            categories.append(category_data)

        # Sort by sort_order
        categories.sort(key=lambda x: x.get("sort_order", 0))
        return categories

    def get_category(self, category_id: str) -> Optional[Dict]:
        """
        Get a specific category by ID.

        Args:
            category_id: The category ID (e.g., "FOOD_OUT")

        Returns:
            Category dict or None if not found
        """
        if not self.user_id:
            raise ValueError("User ID required for user-scoped categories")

        doc = self.db.collection(self._get_collection_path("categories")).document(category_id).get()

        if not doc.exists:
            return None

        category_data = doc.to_dict()
        category_data["category_id"] = doc.id
        return category_data

    def create_category(self, category_data: Dict) -> str:
        """
        Create a new category for the user.

        Args:
            category_data: Category data including display_name, icon, color, monthly_cap

        Returns:
            The new category ID

        Raises:
            ValueError: If max categories reached or name already exists
        """
        if not self.user_id:
            raise ValueError("User ID required for user-scoped categories")

        # Check max categories limit
        existing = self.get_user_categories()
        if len(existing) >= MAX_CATEGORIES:
            raise ValueError(f"Maximum of {MAX_CATEGORIES} categories allowed")

        # Generate category ID from display name
        category_id = generate_category_id(category_data["display_name"])

        # Check for duplicate name (case-insensitive)
        display_name_lower = category_data["display_name"].lower()
        for cat in existing:
            if cat.get("display_name", "").lower() == display_name_lower:
                raise ValueError(f"Category '{category_data['display_name']}' already exists")

        # Get next sort_order
        max_sort = max([c.get("sort_order", 0) for c in existing], default=-1)

        # Prepare document data
        doc_data = {
            "display_name": category_data["display_name"],
            "icon": category_data["icon"],
            "color": category_data["color"],
            "monthly_cap": category_data["monthly_cap"],
            "is_system": category_data.get("is_system", False),
            "sort_order": max_sort + 1,
            "created_at": firestore.SERVER_TIMESTAMP,
            "exclude_from_total": category_data.get("exclude_from_total", False)
        }

        # Save to Firestore
        self.db.collection(self._get_collection_path("categories")).document(category_id).set(doc_data)

        return category_id

    def update_category(self, category_id: str, updates: Dict) -> bool:
        """
        Update a category's fields.

        Args:
            category_id: The category ID
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if category not found
        """
        if not self.user_id:
            raise ValueError("User ID required for user-scoped categories")

        doc_ref = self.db.collection(self._get_collection_path("categories")).document(category_id)

        if not doc_ref.get().exists:
            raise DocumentNotFoundError("categories", category_id)

        # Filter out None values
        filtered_updates = {k: v for k, v in updates.items() if v is not None}

        if filtered_updates:
            doc_ref.update(filtered_updates)

        return True

    def delete_category(self, category_id: str, reassign_to: str = "OTHER") -> int:
        """
        Delete a category and reassign its expenses to another category.

        Args:
            category_id: The category to delete
            reassign_to: The category to reassign expenses to (default: OTHER)

        Returns:
            Number of expenses reassigned

        Raises:
            ValueError: If trying to delete the OTHER category
        """
        if not self.user_id:
            raise ValueError("User ID required for user-scoped categories")

        # Cannot delete OTHER category
        if category_id == "OTHER":
            raise ValueError("Cannot delete the OTHER category")

        # Get category to verify it exists
        category = self.get_category(category_id)
        if not category:
            raise ValueError(f"Category '{category_id}' not found")

        if category.get("is_system"):
            raise ValueError("Cannot delete system categories")

        # Reassign all expenses with this category to the target category
        expenses_ref = self.db.collection(self._get_collection_path("expenses"))
        expenses_to_update = expenses_ref.where(
            filter=FieldFilter("category", "==", category_id)
        ).stream()

        reassigned_count = 0
        for expense_doc in expenses_to_update:
            expense_doc.reference.update({"category": reassign_to})
            reassigned_count += 1

        # Also update recurring expenses
        recurring_ref = self.db.collection(self._get_collection_path("recurring_expenses"))
        recurring_to_update = recurring_ref.where(
            filter=FieldFilter("category", "==", category_id)
        ).stream()

        for recurring_doc in recurring_to_update:
            recurring_doc.reference.update({"category": reassign_to})

        # Delete the category
        self.db.collection(self._get_collection_path("categories")).document(category_id).delete()

        return reassigned_count

    def reorder_categories(self, category_ids: List[str]) -> bool:
        """
        Update the sort order of categories.

        Args:
            category_ids: List of category IDs in desired order

        Returns:
            True if successful
        """
        if not self.user_id:
            raise ValueError("User ID required for user-scoped categories")

        # Update each category's sort_order
        for index, category_id in enumerate(category_ids):
            doc_ref = self.db.collection(self._get_collection_path("categories")).document(category_id)
            if doc_ref.get().exists:
                doc_ref.update({"sort_order": index})

        return True

    # ==================== Total Budget Operations ====================

    def get_total_monthly_budget(self) -> float:
        """
        Get the user's total monthly budget.

        Returns:
            Total monthly budget amount
        """
        if not self.user_id:
            # Fallback to old TOTAL cap
            return self.get_budget_cap("TOTAL") or 0

        user_doc = self.db.collection("users").document(self.user_id).get()

        if user_doc.exists:
            data = user_doc.to_dict()
            return data.get("total_monthly_budget", 0)

        return 0

    def set_total_monthly_budget(self, amount: float) -> bool:
        """
        Set the user's total monthly budget.

        Args:
            amount: The total monthly budget

        Returns:
            True if successful
        """
        if not self.user_id:
            raise ValueError("User ID required for total budget")

        self.db.collection("users").document(self.user_id).set({
            "total_monthly_budget": amount
        }, merge=True)

        return True

    def recalculate_other_cap(self) -> float:
        """
        Recalculate the OTHER category cap based on total budget minus other caps.

        OTHER cap = total_budget - sum(all_other_category_caps)

        Returns:
            The new OTHER cap value
        """
        if not self.user_id:
            raise ValueError("User ID required for recalculate")

        total_budget = self.get_total_monthly_budget()
        categories = self.get_user_categories()

        # Sum all caps except OTHER
        allocated = sum(
            cat.get("monthly_cap", 0)
            for cat in categories
            if cat.get("category_id") != "OTHER"
        )

        # OTHER gets the remainder (can be 0 or negative if over-allocated)
        other_cap = max(0, total_budget - allocated)

        # Update OTHER category
        self.update_category("OTHER", {"monthly_cap": other_cap})

        return other_cap

    # ==================== Category Migration Operations ====================

    def has_categories_setup(self) -> bool:
        """
        Check if the user has custom categories set up.

        Returns:
            True if user has categories in their categories collection
        """
        if not self.user_id:
            return False

        # Check if categories collection has documents
        categories_ref = self.db.collection(self._get_collection_path("categories"))
        docs = categories_ref.limit(1).stream()

        return any(True for _ in docs)

    def migrate_from_budget_caps(self) -> bool:
        """
        Migrate user from old budget_caps collection to new categories collection.

        1. Read existing budget_caps
        2. Create category docs with icons/colors from defaults
        3. Set total_monthly_budget from TOTAL cap
        4. Ensure OTHER exists

        Returns:
            True if migration performed, False if already migrated
        """
        if not self.user_id:
            raise ValueError("User ID required for migration")

        # Check if already migrated
        if self.has_categories_setup():
            return False

        # Get existing budget caps
        old_caps = self.get_all_budget_caps()

        if not old_caps:
            # No old data, initialize with defaults
            return self.initialize_default_categories(0, list(DEFAULT_CATEGORIES.keys()))

        # Extract total budget
        total_budget = old_caps.pop("TOTAL", 0)

        # Create categories from old caps
        sort_order = 0
        for category_id, cap in old_caps.items():
            defaults = DEFAULT_CATEGORIES.get(category_id, {})

            category_data = {
                "display_name": defaults.get("display_name", category_id.replace("_", " ").title()),
                "icon": defaults.get("icon", "circle"),
                "color": defaults.get("color", "#6B7280"),
                "monthly_cap": cap,
                "is_system": defaults.get("is_system", False),
                "sort_order": sort_order,
                "created_at": firestore.SERVER_TIMESTAMP,
                "exclude_from_total": False
            }

            self.db.collection(self._get_collection_path("categories")).document(category_id).set(category_data)
            sort_order += 1

        # Ensure OTHER exists
        if "OTHER" not in old_caps:
            other_defaults = DEFAULT_CATEGORIES.get("OTHER", {})
            other_data = {
                "display_name": other_defaults.get("display_name", "Other"),
                "icon": other_defaults.get("icon", "more-horizontal"),
                "color": other_defaults.get("color", "#6B7280"),
                "monthly_cap": 0,
                "is_system": True,
                "sort_order": sort_order,
                "created_at": firestore.SERVER_TIMESTAMP,
                "exclude_from_total": False
            }
            self.db.collection(self._get_collection_path("categories")).document("OTHER").set(other_data)

        # Set total budget
        self.set_total_monthly_budget(total_budget)

        # Recalculate OTHER cap
        self.recalculate_other_cap()

        return True

    def initialize_default_categories(self, total_budget: float, selected_ids: List[str]) -> bool:
        """
        Initialize categories for a new user with selected defaults.

        Args:
            total_budget: The total monthly budget
            selected_ids: List of default category IDs to create

        Returns:
            True if successful
        """
        if not self.user_id:
            raise ValueError("User ID required for initialization")

        # Ensure OTHER is always included
        if "OTHER" not in selected_ids:
            selected_ids.append("OTHER")

        # Create selected categories
        sort_order = 0
        for category_id in selected_ids:
            defaults = DEFAULT_CATEGORIES.get(category_id, {})

            if not defaults:
                continue

            category_data = {
                "display_name": defaults.get("display_name", category_id.replace("_", " ").title()),
                "icon": defaults.get("icon", "circle"),
                "color": defaults.get("color", "#6B7280"),
                "monthly_cap": 0,  # Start with 0, user will allocate
                "is_system": defaults.get("is_system", False),
                "sort_order": sort_order,
                "created_at": firestore.SERVER_TIMESTAMP,
                "exclude_from_total": False
            }

            self.db.collection(self._get_collection_path("categories")).document(category_id).set(category_data)
            sort_order += 1

        # Set total budget
        self.set_total_monthly_budget(total_budget)

        return True

    def get_category_cap(self, category_id: str) -> Optional[float]:
        """
        Get the budget cap for a specific category.

        Args:
            category_id: The category ID

        Returns:
            Monthly cap amount or None if category not found
        """
        category = self.get_category(category_id)
        if category:
            return category.get("monthly_cap")
        return None

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

    def save_recurring_expense(self, recurring: RecurringExpense, category_str: Optional[str] = None) -> str:
        """
        Save a recurring expense template to Firestore.

        Args:
            recurring: RecurringExpense object
            category_str: Optional category ID string override (e.g., "PET_SUPPLIES").
                          If provided, uses this instead of recurring.category.name.

        Returns:
            Document ID of the saved recurring expense
        """
        recurring_data = {
            "expense_name": recurring.expense_name,
            "amount": recurring.amount,
            "category": category_str if category_str else recurring.category.name,
            "frequency": recurring.frequency.value,
            "day_of_month": recurring.day_of_month,
            "day_of_week": recurring.day_of_week,
            "month_of_year": recurring.month_of_year,
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
        try:
            doc_ref = self.db.collection(self._get_collection_path("recurring_expenses")).add(recurring_data)
            return doc_ref[1].id
        except GoogleAPIError as e:
            logger.error("Firestore write failed in save_recurring_expense: %s", e)
            raise RuntimeError(f"Failed to save recurring expense: {e}") from e

    def get_recurring_expense(self, template_id: str) -> Optional[RecurringExpense]:
        """
        Get a specific recurring expense by ID.

        Args:
            template_id: Document ID

        Returns:
            RecurringExpense object or None
        """
        doc = self.db.collection(self._get_collection_path("recurring_expenses")).document(template_id).get()

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
        query = self.db.collection(self._get_collection_path("recurring_expenses"))

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
        self.db.collection(self._get_collection_path("recurring_expenses")).document(template_id).update(updates)

    def delete_recurring_expense(self, template_id: str) -> None:
        """
        Delete a recurring expense template (or mark as inactive).

        Args:
            template_id: Document ID
        """
        # Mark as inactive instead of deleting
        self.db.collection(self._get_collection_path("recurring_expenses")).document(template_id).update({"active": False})

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
            month_of_year=data.get("month_of_year"),
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
        doc_ref = self.db.collection(self._get_collection_path("pending_expenses")).add(pending_data)
        return doc_ref[1].id

    def get_pending_expense(self, pending_id: str) -> Optional[PendingExpense]:
        """
        Get a specific pending expense by ID.

        Args:
            pending_id: Document ID

        Returns:
            PendingExpense object or None
        """
        doc = self.db.collection(self._get_collection_path("pending_expenses")).document(pending_id).get()

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
        query = self.db.collection(self._get_collection_path("pending_expenses"))

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
        query = self.db.collection(self._get_collection_path("pending_expenses")).where(
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
        self.db.collection(self._get_collection_path("pending_expenses")).document(pending_id).update(updates)

    def delete_pending_expense(self, pending_id: str) -> None:
        """
        Delete a pending expense.

        Args:
            pending_id: Document ID
        """
        self.db.collection(self._get_collection_path("pending_expenses")).document(pending_id).delete()

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

    # ==================== Conversation History Operations ====================

    def create_conversation(self) -> str:
        """
        Create a new conversation and return its ID.

        Returns:
            Document ID of the new conversation
        """
        conversation_data = {
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_activity": firestore.SERVER_TIMESTAMP,
            "messages": [],
            "summary": None,
            "recent_expenses": []  # Track recent expenses for context
        }

        doc_ref = self.db.collection(self._get_collection_path("conversations")).add(conversation_data)
        return doc_ref[1].id

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Get a specific conversation by ID.

        Args:
            conversation_id: Firestore document ID

        Returns:
            Conversation dict or None if not found
        """
        doc = self.db.collection(self._get_collection_path("conversations")).document(conversation_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        data["conversation_id"] = doc.id
        return data

    def list_conversations(self, limit: int = 20) -> List[Dict]:
        """
        List recent conversations, ordered by last activity.

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversation dicts with conversation_id
        """
        query = self.db.collection(self._get_collection_path("conversations"))
        query = query.order_by("last_activity", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)

        docs = query.stream()

        conversations = []
        for doc in docs:
            data = doc.to_dict()
            data["conversation_id"] = doc.id
            conversations.append(data)

        return conversations

    def add_message_to_conversation(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: list = None
    ) -> bool:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Firestore document ID
            role: Message role ("user" or "assistant")
            content: Message content
            tool_calls: Optional list of tool call dicts with id, name, args, result

        Returns:
            True if successful, False if conversation not found
        """
        doc_ref = self.db.collection(self._get_collection_path("conversations")).document(conversation_id)

        # Check if conversation exists
        if not doc_ref.get().exists:
            raise DocumentNotFoundError("conversations", conversation_id)

        # Get current time for message timestamp
        import pytz
        user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)

        message = {
            "role": role,
            "content": content,
            "timestamp": now.isoformat()
        }

        if tool_calls:
            message["tool_calls"] = tool_calls

        # Use array union to add message
        doc_ref.update({
            "messages": firestore.ArrayUnion([message]),
            "last_activity": firestore.SERVER_TIMESTAMP
        })

        return True

    def update_conversation_summary(self, conversation_id: str, summary: str) -> bool:
        """
        Update the summary of a conversation.

        Args:
            conversation_id: Firestore document ID
            summary: Brief summary of the conversation

        Returns:
            True if successful, False if conversation not found
        """
        doc_ref = self.db.collection(self._get_collection_path("conversations")).document(conversation_id)

        if not doc_ref.get().exists:
            raise DocumentNotFoundError("conversations", conversation_id)

        doc_ref.update({"summary": summary})
        return True

    def update_conversation_recent_expenses(
        self,
        conversation_id: str,
        expense_id: str,
        expense_name: str,
        amount: float,
        category: str,
        date: Optional[Dict] = None
    ) -> bool:
        """
        Update the recent expenses tracked in a conversation (for context).

        Keeps last 5 expenses for "that expense" / "the last one" references.

        Args:
            conversation_id: Firestore document ID
            expense_id: Firebase expense document ID
            expense_name: Human-readable expense name
            amount: Dollar amount
            category: Expense category
            date: Optional date dict {day, month, year}

        Returns:
            True if successful, False if conversation not found
        """
        doc_ref = self.db.collection(self._get_collection_path("conversations")).document(conversation_id)

        doc = doc_ref.get()
        if not doc.exists:
            raise DocumentNotFoundError("conversations", conversation_id)

        data = doc.to_dict()
        recent_expenses = data.get("recent_expenses", [])

        # Add new expense to front
        expense_data = {
            "expense_id": expense_id,
            "expense_name": expense_name,
            "amount": amount,
            "category": category,
            "date": date
        }

        recent_expenses.insert(0, expense_data)
        recent_expenses = recent_expenses[:5]  # Keep last 5

        doc_ref.update({
            "recent_expenses": recent_expenses,
            "last_activity": firestore.SERVER_TIMESTAMP
        })

        return True

    def get_conversation_recent_expenses(self, conversation_id: str, limit: int = 5) -> List[Dict]:
        """
        Get recent expenses from a conversation for context.

        Args:
            conversation_id: Firestore document ID
            limit: Maximum number of expenses to return

        Returns:
            List of recent expense dicts
        """
        doc = self.db.collection(self._get_collection_path("conversations")).document(conversation_id).get()

        if not doc.exists:
            return []

        data = doc.to_dict()
        recent_expenses = data.get("recent_expenses", [])
        return recent_expenses[:limit]

    def add_deleted_expense_to_conversation(self, conversation_id: str, expense_id: str) -> bool:
        """
        Append an expense ID to a conversation's deleted_expense_ids array.

        Uses Firestore ArrayUnion for an atomic, lightweight update
        without reading/writing the full messages array.

        Args:
            conversation_id: Firestore document ID of the conversation
            expense_id: The expense ID to mark as deleted

        Returns:
            True if successful, False if conversation not found
        """
        doc_ref = self.db.collection(self._get_collection_path("conversations")).document(conversation_id)

        if not doc_ref.get().exists:
            raise DocumentNotFoundError("conversations", conversation_id)

        doc_ref.update({
            "deleted_expense_ids": firestore.ArrayUnion([expense_id])
        })
        return True

    def verify_expenses_exist(self, expense_ids: list) -> list:
        """
        Check which expense IDs still exist in Firestore.

        Args:
            expense_ids: List of expense document IDs to check

        Returns:
            List of expense IDs that still exist
        """
        if not expense_ids:
            return []

        existing = []
        expenses_col = self._get_collection_path("expenses")
        for eid in expense_ids:
            doc = self.db.collection(expenses_col).document(eid).get()
            if doc.exists:
                existing.append(eid)
        return existing

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Firestore document ID

        Returns:
            True if deleted, False if not found
        """
        doc_ref = self.db.collection(self._get_collection_path("conversations")).document(conversation_id)

        if not doc_ref.get().exists:
            raise DocumentNotFoundError("conversations", conversation_id)

        doc_ref.delete()
        return True

    def cleanup_old_conversations(self, ttl_hours: int = 24) -> int:
        """
        Delete conversations older than TTL.

        Args:
            ttl_hours: Time-to-live in hours (default 24)

        Returns:
            Number of conversations deleted
        """
        import pytz
        from datetime import timedelta

        user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
        tz = pytz.timezone(user_timezone)
        cutoff = datetime.now(tz) - timedelta(hours=ttl_hours)

        query = self.db.collection(self._get_collection_path("conversations"))
        query = query.where(filter=FieldFilter("last_activity", "<", cutoff))

        docs = query.stream()

        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1

        return deleted_count

    # ==================== User Settings Operations ====================

    def get_user_settings(self, user_id: str) -> dict:
        """
        Return the users/{uid} document as a dict.

        Defaults to {"selected_model": DEFAULT_MODEL} if the document doesn't exist
        or the field is missing.

        Args:
            user_id: Firebase Auth UID

        Returns:
            Dict with at least a "selected_model" key
        """
        from .model_client import DEFAULT_MODEL

        doc = self.db.collection("users").document(user_id).get()
        if doc.exists:
            data = doc.to_dict() or {}
            if "selected_model" not in data:
                data["selected_model"] = DEFAULT_MODEL
            return data
        return {"selected_model": DEFAULT_MODEL}

    def update_user_settings(self, user_id: str, settings: dict) -> None:
        """
        Merge *settings* into the users/{uid} document (set with merge=True).

        Args:
            user_id: Firebase Auth UID
            settings: Dict of settings fields to update (e.g. {"selected_model": "gpt-5-mini"})
        """
        self.db.collection("users").document(user_id).set(settings, merge=True)

    def log_token_usage(
        self,
        user_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        endpoint: str,
    ) -> None:
        """
        Write a token usage record to users/{uid}/token_usage/ subcollection.

        Args:
            user_id:       Firebase Auth UID
            model:         Model identifier (e.g. "claude-sonnet-4-6")
            provider:      Provider name ("anthropic" | "openai" | "google")
            input_tokens:  Number of input/prompt tokens consumed
            output_tokens: Number of output/completion tokens consumed
            endpoint:      API endpoint that triggered the call ("chat" | "process_expense")
        """
        record = {
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "endpoint": endpoint,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
        try:
            self.db.collection("users").document(user_id).collection("token_usage").add(record)
        except Exception as exc:
            # Token logging is non-critical — log and continue
            logger.warning("Failed to log token usage for user %s: %s", user_id, exc)

    @classmethod
    def cleanup_all_users_conversations(cls, ttl_hours: int = 24) -> Dict[str, int]:
        """
        Delete old conversations for ALL users. Used by admin cleanup endpoint.

        Args:
            ttl_hours: Time-to-live in hours (default 24)

        Returns:
            Dict with user_id -> deleted_count
        """
        # Get a global client to iterate users
        global_client = cls()
        users_ref = global_client.db.collection("users")
        user_docs = users_ref.stream()

        results = {}
        total_deleted = 0

        for user_doc in user_docs:
            user_id = user_doc.id
            user_client = cls.for_user(user_id)
            deleted = user_client.cleanup_old_conversations(ttl_hours)

            if deleted > 0:
                results[user_id] = deleted
                total_deleted += deleted

        results["_total"] = total_deleted
        return results
