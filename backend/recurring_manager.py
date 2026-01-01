"""
Recurring Manager - Core logic for recurring expenses and confirmations.

Handles:
- Checking for due recurring expenses
- Creating pending expenses
- Calculating trigger dates
- Confirmation/skip/cancel flows
"""

import os
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from calendar import monthrange
import pytz

from .output_schemas import (
    RecurringExpense,
    PendingExpense,
    Expense,
    Date,
    FrequencyType,
    ExpenseType
)


def get_today_in_user_timezone() -> date:
    """
    Get today's date in the user's timezone (not UTC).

    Returns:
        Today's date in the user's timezone
    """
    user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
    tz = pytz.timezone(user_timezone)
    return datetime.now(tz).date()


class RecurringManager:
    """Manages recurring expense logic and pending confirmations."""

    @staticmethod
    def calculate_next_trigger_date(recurring: RecurringExpense, from_date: Optional[date] = None) -> date:
        """
        Calculate the next trigger date for a recurring expense.

        Args:
            recurring: RecurringExpense object
            from_date: Calculate from this date (defaults to today)

        Returns:
            The next trigger date
        """
        if from_date is None:
            from_date = get_today_in_user_timezone()

        if recurring.frequency == FrequencyType.MONTHLY:
            return RecurringManager._calculate_next_monthly(recurring, from_date)
        elif recurring.frequency == FrequencyType.WEEKLY:
            return RecurringManager._calculate_next_weekly(recurring, from_date)
        elif recurring.frequency == FrequencyType.BIWEEKLY:
            return RecurringManager._calculate_next_biweekly(recurring, from_date)
        else:
            raise ValueError(f"Unsupported frequency: {recurring.frequency}")

    @staticmethod
    def _calculate_next_monthly(recurring: RecurringExpense, from_date: date) -> date:
        """Calculate next monthly trigger date."""
        if recurring.last_of_month:
            # Last day of month logic
            year = from_date.year
            month = from_date.month

            # Get last day of current month
            last_day = monthrange(year, month)[1]
            trigger_date = date(year, month, last_day)

            # If already passed, move to next month
            if trigger_date <= from_date:
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                last_day = monthrange(year, month)[1]
                trigger_date = date(year, month, last_day)

            return trigger_date
        else:
            # Specific day of month
            target_day = recurring.day_of_month
            year = from_date.year
            month = from_date.month

            # Handle case where month doesn't have that day (e.g., Feb 31 → Feb 28/29)
            last_day_of_month = monthrange(year, month)[1]
            actual_day = min(target_day, last_day_of_month)

            trigger_date = date(year, month, actual_day)

            # If already passed, move to next month
            if trigger_date <= from_date:
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1

                last_day_of_month = monthrange(year, month)[1]
                actual_day = min(target_day, last_day_of_month)
                trigger_date = date(year, month, actual_day)

            return trigger_date

    @staticmethod
    def _calculate_next_weekly(recurring: RecurringExpense, from_date: date) -> date:
        """Calculate next weekly trigger date."""
        target_weekday = recurring.day_of_week  # 0=Monday, 6=Sunday
        current_weekday = from_date.weekday()

        # Calculate days until target weekday
        days_ahead = (target_weekday - current_weekday) % 7

        # If 0, means it's today - move to next week
        if days_ahead == 0:
            days_ahead = 7

        return from_date + timedelta(days=days_ahead)

    @staticmethod
    def _calculate_next_biweekly(recurring: RecurringExpense, from_date: date) -> date:
        """Calculate next biweekly trigger date."""
        # Similar to weekly but every 2 weeks
        # For simplicity, calculate next weekly occurrence + 7 days
        next_weekly = RecurringManager._calculate_next_weekly(recurring, from_date)

        # If last_reminded exists and it's from this week, skip to next week
        if recurring.last_reminded:
            last_reminded_date = date(
                recurring.last_reminded.year,
                recurring.last_reminded.month,
                recurring.last_reminded.day
            )
            # Check if last_reminded was within the past 13 days
            days_since_last = (from_date - last_reminded_date).days
            if days_since_last < 14:
                # Skip this week, go to next occurrence
                return next_weekly + timedelta(days=7)

        return next_weekly

    @staticmethod
    def calculate_most_recent_trigger_date(recurring: RecurringExpense, as_of_date: Optional[date] = None) -> date:
        """
        Calculate the most recent trigger date that should have occurred.

        This is used to determine if we need to create a pending expense.

        Args:
            recurring: RecurringExpense object
            as_of_date: Calculate as of this date (defaults to today)

        Returns:
            The most recent trigger date that should have occurred
        """
        if as_of_date is None:
            as_of_date = get_today_in_user_timezone()

        if recurring.frequency == FrequencyType.MONTHLY:
            return RecurringManager._calculate_most_recent_monthly(recurring, as_of_date)
        elif recurring.frequency == FrequencyType.WEEKLY:
            return RecurringManager._calculate_most_recent_weekly(recurring, as_of_date)
        elif recurring.frequency == FrequencyType.BIWEEKLY:
            return RecurringManager._calculate_most_recent_biweekly(recurring, as_of_date)
        else:
            raise ValueError(f"Unsupported frequency: {recurring.frequency}")

    @staticmethod
    def _calculate_most_recent_monthly(recurring: RecurringExpense, as_of_date: date) -> date:
        """Calculate most recent monthly trigger date."""
        if recurring.last_of_month:
            # Last day of current month
            year = as_of_date.year
            month = as_of_date.month
            last_day = monthrange(year, month)[1]
            trigger_date = date(year, month, last_day)

            # If trigger hasn't happened yet this month, use last month
            if trigger_date > as_of_date:
                if month == 1:
                    year -= 1
                    month = 12
                else:
                    month -= 1
                last_day = monthrange(year, month)[1]
                trigger_date = date(year, month, last_day)

            return trigger_date
        else:
            # Specific day of month
            target_day = recurring.day_of_month
            year = as_of_date.year
            month = as_of_date.month

            # Handle case where month doesn't have that day
            last_day_of_month = monthrange(year, month)[1]
            actual_day = min(target_day, last_day_of_month)

            trigger_date = date(year, month, actual_day)

            # If trigger hasn't happened yet this month, use last month
            if trigger_date > as_of_date:
                if month == 1:
                    year -= 1
                    month = 12
                else:
                    month -= 1

                last_day_of_month = monthrange(year, month)[1]
                actual_day = min(target_day, last_day_of_month)
                trigger_date = date(year, month, actual_day)

            return trigger_date

    @staticmethod
    def _calculate_most_recent_weekly(recurring: RecurringExpense, as_of_date: date) -> date:
        """Calculate most recent weekly trigger date."""
        target_weekday = recurring.day_of_week
        current_weekday = as_of_date.weekday()

        # Calculate days back to target weekday
        days_back = (current_weekday - target_weekday) % 7

        # If 0, means it's today
        if days_back == 0:
            return as_of_date

        return as_of_date - timedelta(days=days_back)

    @staticmethod
    def _calculate_most_recent_biweekly(recurring: RecurringExpense, as_of_date: date) -> date:
        """Calculate most recent biweekly trigger date."""
        # Get most recent weekly occurrence
        most_recent_weekly = RecurringManager._calculate_most_recent_weekly(recurring, as_of_date)

        # Check if this is the biweekly occurrence based on last_reminded
        if recurring.last_reminded:
            last_reminded_date = date(
                recurring.last_reminded.year,
                recurring.last_reminded.month,
                recurring.last_reminded.day
            )
            days_since_last = (most_recent_weekly - last_reminded_date).days

            # If last reminder was less than 14 days before most recent weekly, go back another week
            if 0 < days_since_last < 14:
                return most_recent_weekly - timedelta(days=7)

        return most_recent_weekly

    @staticmethod
    def should_create_pending(recurring: RecurringExpense) -> Tuple[bool, Optional[date]]:
        """
        Determine if we should create a pending expense for this recurring expense.

        Logic:
        1. Calculate most recent trigger date
        2. If last_reminded < trigger_date: Create pending
        3. If last_reminded >= trigger_date AND last_user_action > last_reminded: Already handled
        4. If last_reminded >= trigger_date AND last_user_action < last_reminded: Still pending

        Args:
            recurring: RecurringExpense object

        Returns:
            Tuple of (should_create: bool, trigger_date: Optional[date])
        """
        if not recurring.active:
            return False, None

        trigger_date = RecurringManager.calculate_most_recent_trigger_date(recurring)

        # Convert trigger_date to Date object for comparison
        trigger_date_obj = Date(day=trigger_date.day, month=trigger_date.month, year=trigger_date.year)

        # If never reminded, create pending
        if recurring.last_reminded is None:
            return True, trigger_date

        # Compare dates
        last_reminded = recurring.last_reminded
        last_reminded_as_date = date(last_reminded.year, last_reminded.month, last_reminded.day)

        if last_reminded_as_date < trigger_date:
            # Need to create pending expense
            return True, trigger_date
        elif last_reminded_as_date >= trigger_date:
            # Already reminded for this period
            if recurring.last_user_action:
                last_action = recurring.last_user_action
                last_action_as_date = date(last_action.year, last_action.month, last_action.day)

                if last_action_as_date > last_reminded_as_date:
                    # User already handled it
                    return False, None
                else:
                    # Still pending (user hasn't responded)
                    # Don't create duplicate, but it should show in Streamlit
                    return False, None
            else:
                # No user action yet, still pending
                return False, None

        return False, None

    @staticmethod
    def create_pending_expense_from_recurring(
        recurring: RecurringExpense,
        trigger_date: date
    ) -> PendingExpense:
        """
        Create a PendingExpense from a RecurringExpense.

        Args:
            recurring: RecurringExpense template
            trigger_date: Date the expense is due

        Returns:
            PendingExpense object
        """
        return PendingExpense(
            template_id=recurring.template_id,
            expense_name=recurring.expense_name,
            amount=recurring.amount,
            date=Date(day=trigger_date.day, month=trigger_date.month, year=trigger_date.year),
            category=recurring.category,
            sms_sent=False,
            awaiting_confirmation=True
        )

    @staticmethod
    def pending_to_expense(pending: PendingExpense, adjusted_amount: Optional[float] = None) -> Expense:
        """
        Convert a PendingExpense to a confirmed Expense.

        Args:
            pending: PendingExpense to confirm
            adjusted_amount: Optional adjusted amount (if user replied with different amount)

        Returns:
            Expense object ready to save
        """
        return Expense(
            expense_name=pending.expense_name,
            amount=adjusted_amount if adjusted_amount is not None else pending.amount,
            date=pending.date,
            category=pending.category
        )

    @staticmethod
    def format_confirmation_sms(
        pending: PendingExpense,
        pending_count: int = 0,
        total_pending: int = 0
    ) -> str:
        """
        Format SMS message for pending expense confirmation.

        Args:
            pending: PendingExpense to confirm
            pending_count: Current position in queue (0 if first/only)
            total_pending: Total number of pending expenses due today

        Returns:
            Formatted SMS message
        """
        # Get emoji for category
        emoji_map = {
            ExpenseType.FOOD_OUT: "🍽️",
            ExpenseType.RENT: "🏠",
            ExpenseType.UTILITIES: "💡",
            ExpenseType.MEDICAL: "🏥",
            ExpenseType.GAS: "⛽",
            ExpenseType.GROCERIES: "🛒",
            ExpenseType.RIDE_SHARE: "🚕",
            ExpenseType.COFFEE: "☕",
            ExpenseType.HOTEL: "🏨",
            ExpenseType.TECH: "💻",
            ExpenseType.TRAVEL: "✈️",
            ExpenseType.OTHER: "📦"
        }

        emoji = emoji_map.get(pending.category, "📦")

        # Base message
        message = f"{emoji} {pending.expense_name} ${pending.amount:.2f} due {pending.date.month}/{pending.date.day}/{pending.date.year}."

        # Add count if multiple pending
        if total_pending > 1:
            if pending_count == 0:
                message = f"You have {total_pending} recurring expenses due today. " + message
            else:
                remaining = total_pending - pending_count
                message += f" ({remaining} remaining)"

        message += " Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"

        return message

    @staticmethod
    def parse_confirmation_response(response: str) -> Tuple[str, Optional[float]]:
        """
        Parse user's response to confirmation SMS.

        Args:
            response: User's SMS response

        Returns:
            Tuple of (action: str, adjusted_amount: Optional[float])
            action can be: "YES", "SKIP", "CANCEL", "DELETE", "UNKNOWN"
        """
        response_lower = response.strip().lower()

        # Check for exact matches first
        if response_lower == "yes":
            return "YES", None
        elif response_lower == "skip":
            return "SKIP", None
        elif response_lower == "cancel":
            return "CANCEL", None
        elif response_lower == "delete":
            return "DELETE", None

        # Check for YES with amount (e.g., "yes $1050" or "yes 1050")
        if response_lower.startswith("yes"):
            # Try to extract amount
            import re
            # Match patterns like "yes $1050", "yes 1050", "yes $1,050.50"
            amount_match = re.search(r'\$?\s*([\d,]+\.?\d*)', response_lower[3:])
            if amount_match:
                try:
                    amount_str = amount_match.group(1).replace(',', '')
                    amount = float(amount_str)
                    return "YES", amount
                except ValueError:
                    pass
            return "YES", None

        return "UNKNOWN", None
