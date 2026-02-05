"""
Budget Manager - Handles budget calculations and warning generation.
"""

from typing import Optional, Dict, Union
from datetime import datetime

from .firebase_client import FirebaseClient
from .output_schemas import ExpenseType


class BudgetManager:
    """Manages budget tracking, calculations, and warning messages."""

    def __init__(self, firebase_client: Optional[FirebaseClient] = None):
        """
        Initialize BudgetManager.

        Args:
            firebase_client: Optional FirebaseClient instance (creates new one if not provided)
        """
        self.firebase = firebase_client or FirebaseClient()

    def calculate_monthly_spending(self, category: Union[ExpenseType, str], year: int, month: int) -> float:
        """
        Calculate total spending for a specific category in a given month.

        Args:
            category: The expense category (ExpenseType or string ID)
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Total amount spent in the category for the month
        """
        # Handle both ExpenseType and string
        if isinstance(category, ExpenseType):
            return self.firebase.calculate_monthly_total(year, month, category)
        else:
            # String category ID - calculate from monthly expenses
            return self.calculate_monthly_spending_for_category_id(category, year, month)

    def calculate_monthly_spending_for_category_id(self, category_id: str, year: int, month: int) -> float:
        """
        Calculate total spending for a category by string ID.

        Args:
            category_id: The category ID string (e.g., "FOOD_OUT", "PET_SUPPLIES")
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Total amount spent in the category for the month
        """
        # Get all expenses for the month
        expenses = self.firebase.get_monthly_expenses(year, month, category=None)

        # Sum amounts for matching category
        total = 0
        for expense in expenses:
            if expense.get("category") == category_id:
                total += expense.get("amount", 0)

        return total

    def calculate_total_monthly_spending(self, year: int, month: int) -> float:
        """
        Calculate total spending across all categories for a given month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Total amount spent across all categories for the month
        """
        return self.firebase.calculate_monthly_total(year, month, category=None)

    def get_monthly_spending_by_category(self, year: int, month: int) -> Dict[str, float]:
        """
        OPTIMIZED: Get spending totals for ALL categories in a single query.

        Instead of querying Firestore once per category (12+ queries),
        this fetches all expenses for the month in ONE query and groups them in memory.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Dictionary mapping category names to spending amounts
            Example: {"FOOD_OUT": 450.00, "COFFEE": 24.50, ...}
        """
        # Fetch ALL expenses for the month in one query (no category filter)
        all_expenses = self.firebase.get_monthly_expenses(year, month, category=None)

        # Group by category and sum amounts in memory
        category_totals = {}
        for expense in all_expenses:
            category = expense.get("category", "OTHER")
            amount = expense.get("amount", 0)
            category_totals[category] = category_totals.get(category, 0) + amount

        return category_totals

    def get_budget_warning(
        self,
        category: ExpenseType,
        amount: float,
        year: int,
        month: int
    ) -> str:
        """
        Generate budget warning message for a new expense.

        Checks both category-specific budget and total monthly budget.
        Calculates percentages AFTER adding the new expense amount.

        Warning thresholds:
        - 50%: ℹ️ informational
        - 90%: ⚠️ warning
        - 95%: ⚠️ warning
        - 100%+: 🚨 OVER BUDGET

        Category budgets: Warn every time at threshold
        Overall budget: Warn only ONCE per threshold (except 100%+ warns every time)

        Args:
            category: The expense category (ExpenseType)
            amount: The new expense amount to add
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Warning message string (empty if no warnings)
        """
        # Delegate to string-based method
        return self.get_budget_warning_for_category(category.name, amount, year, month)

    def get_budget_warning_for_category(
        self,
        category_id: str,
        amount: float,
        year: int,
        month: int
    ) -> str:
        """
        Generate budget warning message for a new expense using string category ID.

        Supports custom user-defined categories.

        Args:
            category_id: The expense category ID string (e.g., "FOOD_OUT", "PET_SUPPLIES")
            amount: The new expense amount to add
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Warning message string (empty if no warnings)
        """
        warnings = []

        # ==================== Category Budget Check ====================
        # Try to get cap from custom categories first, then fall back to budget_caps
        category_cap = None

        # Check custom categories (for users with custom categories set up)
        if self.firebase.user_id and self.firebase.has_categories_setup():
            category_cap = self.firebase.get_category_cap(category_id)
        else:
            # Fallback to legacy budget_caps
            category_cap = self.firebase.get_budget_cap(category_id)

        if category_cap and category_cap > 0:
            current_category_spending = self.calculate_monthly_spending_for_category_id(category_id, year, month)
            projected_category_spending = current_category_spending + amount

            category_percentage = (projected_category_spending / category_cap) * 100
            category_remaining = category_cap - projected_category_spending

            category_warning = self._format_warning(
                percentage=category_percentage,
                remaining=category_remaining,
                budget_type=f"{category_id} budget",
                cap=category_cap
            )

            if category_warning:
                warnings.append(category_warning)

        # ==================== Total Monthly Budget Check ====================
        # Get total cap from user doc or legacy budget_caps
        if self.firebase.user_id and self.firebase.has_categories_setup():
            total_cap = self.firebase.get_total_monthly_budget()
        else:
            total_cap = self.firebase.get_budget_cap("TOTAL")

        if total_cap and total_cap > 0:
            current_total_spending = self.calculate_total_monthly_spending(year, month)
            projected_total_spending = current_total_spending + amount

            total_percentage = (projected_total_spending / total_cap) * 100
            total_remaining = total_cap - projected_total_spending

            # Determine which threshold we're at
            current_threshold = self._get_threshold_level(total_percentage)

            if current_threshold is not None:
                # Get list of thresholds already warned about this month
                warned_thresholds = self.firebase.get_warned_thresholds(year, month)

                # Decide whether to warn
                should_warn = False
                if current_threshold >= 100:
                    # Over budget: ALWAYS warn (every time)
                    should_warn = True
                elif current_threshold not in warned_thresholds:
                    # New threshold reached: warn and track it
                    should_warn = True

                if should_warn:
                    total_warning = self._format_warning(
                        percentage=total_percentage,
                        remaining=total_remaining,
                        budget_type="monthly total budget",
                        cap=total_cap
                    )

                    if total_warning:
                        warnings.append(total_warning)

                        # Track this threshold (unless already tracked or over 100%)
                        # Over 100% doesn't need tracking since we always warn
                        if current_threshold < 100 and current_threshold not in warned_thresholds:
                            self.firebase.add_warned_threshold(year, month, current_threshold)

        # Combine warnings with line breaks
        return "\n".join(warnings)

    def _get_threshold_level(self, percentage: float) -> Optional[int]:
        """
        Determine which threshold level a percentage falls into.

        Args:
            percentage: Budget usage percentage (e.g., 95.5)

        Returns:
            Threshold level (50, 90, 95, or 100) or None if below 50%
        """
        if percentage >= 100:
            return 100
        elif percentage >= 95:
            return 95
        elif percentage >= 90:
            return 90
        elif percentage >= 50:
            return 50
        else:
            return None

    def _format_warning(
        self,
        percentage: float,
        remaining: float,
        budget_type: str,
        cap: float
    ) -> str:
        """
        Format a budget warning message based on percentage thresholds.

        Args:
            percentage: Budget usage percentage (e.g., 95.5)
            remaining: Dollars remaining (can be negative)
            budget_type: Description of budget (e.g., "COFFEE budget", "monthly total budget")
            cap: The budget cap amount

        Returns:
            Formatted warning message or empty string if no warning needed
        """
        # Determine threshold level
        if percentage >= 100:
            emoji = "🚨"
            prefix = "OVER BUDGET!"
        elif percentage >= 95:
            emoji = "⚠️"
            prefix = None
        elif percentage >= 90:
            emoji = "⚠️"
            prefix = None
        elif percentage >= 50:
            emoji = "ℹ️"
            prefix = None
        else:
            # Below 50% threshold - no warning
            return ""

        # Format remaining amount
        if remaining >= 0:
            remaining_text = f"${remaining:.2f} left"
        else:
            remaining_text = f"${abs(remaining):.2f} over"

        # Build warning message
        if prefix:
            return f"{emoji} {prefix} {percentage:.0f}% of {budget_type} used ({remaining_text})"
        else:
            return f"{emoji} {percentage:.0f}% of {budget_type} used ({remaining_text})"
