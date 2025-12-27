"""
Budget Manager - Handles budget calculations and warning generation.
"""

from typing import Optional
from datetime import datetime

from firebase_client import FirebaseClient
from output_schemas import ExpenseType


class BudgetManager:
    """Manages budget tracking, calculations, and warning messages."""

    def __init__(self, firebase_client: Optional[FirebaseClient] = None):
        """
        Initialize BudgetManager.

        Args:
            firebase_client: Optional FirebaseClient instance (creates new one if not provided)
        """
        self.firebase = firebase_client or FirebaseClient()

    def calculate_monthly_spending(self, category: ExpenseType, year: int, month: int) -> float:
        """
        Calculate total spending for a specific category in a given month.

        Args:
            category: The expense category
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Total amount spent in the category for the month
        """
        return self.firebase.calculate_monthly_total(year, month, category)

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

        Args:
            category: The expense category
            amount: The new expense amount to add
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Warning message string (empty if no warnings)
        """
        warnings = []

        # ==================== Category Budget Check ====================
        category_cap = self.firebase.get_budget_cap(category.name)
        if category_cap and category_cap > 0:
            current_category_spending = self.calculate_monthly_spending(category, year, month)
            projected_category_spending = current_category_spending + amount

            category_percentage = (projected_category_spending / category_cap) * 100
            category_remaining = category_cap - projected_category_spending

            category_warning = self._format_warning(
                percentage=category_percentage,
                remaining=category_remaining,
                budget_type=f"{category.name} budget",
                cap=category_cap
            )

            if category_warning:
                warnings.append(category_warning)

        # ==================== Total Monthly Budget Check ====================
        total_cap = self.firebase.get_budget_cap("TOTAL")
        if total_cap and total_cap > 0:
            current_total_spending = self.calculate_total_monthly_spending(year, month)
            projected_total_spending = current_total_spending + amount

            total_percentage = (projected_total_spending / total_cap) * 100
            total_remaining = total_cap - projected_total_spending

            total_warning = self._format_warning(
                percentage=total_percentage,
                remaining=total_remaining,
                budget_type="monthly total budget",
                cap=total_cap
            )

            if total_warning:
                warnings.append(total_warning)

        # Combine warnings with line breaks
        return "\n".join(warnings)

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
