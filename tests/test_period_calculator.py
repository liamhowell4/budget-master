"""
Tests for backend/period_calculator.py

Only monthly periods are supported. `month_start_day` is either:
- an int 1..28 (specific day of month), or
- the literal string "last" (period starts on the last day of each calendar month).
"""

import pytest
from datetime import date
from backend.period_calculator import (
    BudgetPeriod,
    get_current_period,
    get_period_containing_date,
    navigate_period,
    prorate_cap,
)


# ---------------------------------------------------------------------------
# Monthly (start_day=1) — standard calendar month
# ---------------------------------------------------------------------------

class TestMonthlyCalendar:
    def test_mid_month(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 15))
        assert period.start_date == date(2026, 3, 1)
        assert period.end_date == date(2026, 3, 31)
        assert period.period_id == "monthly-2026-03-01"
        assert period.days_in_period == 31
        assert period.days_elapsed == 15
        assert "March 2026" in period.label

    def test_first_day(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 1, 1))
        assert period.start_date == date(2026, 1, 1)
        assert period.end_date == date(2026, 1, 31)
        assert period.days_elapsed == 1

    def test_last_day(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 2, 28))
        assert period.start_date == date(2026, 2, 1)
        assert period.end_date == date(2026, 2, 28)
        assert period.days_elapsed == 28

    def test_december(self):
        period = get_current_period(month_start_day=1, as_of=date(2025, 12, 25))
        assert period.start_date == date(2025, 12, 1)
        assert period.end_date == date(2025, 12, 31)

    def test_february_leap_year(self):
        period = get_current_period(month_start_day=1, as_of=date(2024, 2, 15))
        assert period.end_date == date(2024, 2, 29)
        assert period.days_in_period == 29

    def test_february_non_leap_year(self):
        period = get_current_period(month_start_day=1, as_of=date(2025, 2, 28))
        assert period.end_date == date(2025, 2, 28)
        assert period.days_in_period == 28


# ---------------------------------------------------------------------------
# Monthly (start_day=N) — custom start day
# ---------------------------------------------------------------------------

class TestMonthlyCustomStartDay:
    def test_on_start_day(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 15))
        assert period.start_date == date(2026, 3, 15)
        assert period.end_date == date(2026, 4, 14)
        assert period.days_elapsed == 1

    def test_after_start_day(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 20))
        assert period.start_date == date(2026, 3, 15)
        assert period.end_date == date(2026, 4, 14)

    def test_before_start_day(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 5))
        assert period.start_date == date(2026, 2, 15)
        assert period.end_date == date(2026, 3, 14)

    def test_period_id_format(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 15))
        assert period.period_id == "monthly-2026-03-15"

    def test_year_boundary_january(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 1, 10))
        assert period.start_date == date(2025, 12, 15)
        assert period.end_date == date(2026, 1, 14)

    def test_year_boundary_december(self):
        period = get_current_period(month_start_day=15, as_of=date(2025, 12, 20))
        assert period.start_date == date(2025, 12, 15)
        assert period.end_date == date(2026, 1, 14)

    def test_days_in_period(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 15))
        assert period.days_in_period == 31


# ---------------------------------------------------------------------------
# Monthly (start_day="last") — last day of month
# ---------------------------------------------------------------------------

class TestMonthlyLastDay:
    def test_as_of_mid_april(self):
        # as_of=2026-04-20 → period = Mar 31 (last of March) → Apr 29 (day before Apr 30, last of April)
        period = get_current_period(month_start_day="last", as_of=date(2026, 4, 20))
        assert period.start_date == date(2026, 3, 31)
        assert period.end_date == date(2026, 4, 29)
        assert period.period_id == "monthly-2026-03-31"

    def test_as_of_last_day_of_month(self):
        # as_of=2026-04-30 (last day of April). The next period starts today.
        period = get_current_period(month_start_day="last", as_of=date(2026, 4, 30))
        assert period.start_date == date(2026, 4, 30)
        assert period.end_date == date(2026, 5, 30)  # day before last of May (May 31)

    def test_as_of_feb_non_leap_year(self):
        # as_of=2025-02-15 (non-leap) → period = Jan 31 → Feb 27
        # (Feb last day is Feb 28, so end = Feb 27)
        period = get_current_period(month_start_day="last", as_of=date(2025, 2, 15))
        assert period.start_date == date(2025, 1, 31)
        assert period.end_date == date(2025, 2, 27)

    def test_as_of_feb_leap_year(self):
        # as_of=2024-02-15 (leap) → period = Jan 31 → Feb 28 (day before Feb 29)
        period = get_current_period(month_start_day="last", as_of=date(2024, 2, 15))
        assert period.start_date == date(2024, 1, 31)
        assert period.end_date == date(2024, 2, 28)

    def test_year_rollover(self):
        # as_of=2026-01-05 → period starts Dec 31 2025, ends Jan 30 2026
        period = get_current_period(month_start_day="last", as_of=date(2026, 1, 5))
        assert period.start_date == date(2025, 12, 31)
        assert period.end_date == date(2026, 1, 30)

    def test_march_boundary_after_28_day_feb(self):
        # as_of=2025-03-05 (non-leap) → period = Feb 28 → Mar 30
        period = get_current_period(month_start_day="last", as_of=date(2025, 3, 5))
        assert period.start_date == date(2025, 2, 28)
        assert period.end_date == date(2025, 3, 30)

    def test_march_boundary_after_29_day_feb(self):
        # as_of=2024-03-05 (leap) → period = Feb 29 → Mar 30
        period = get_current_period(month_start_day="last", as_of=date(2024, 3, 5))
        assert period.start_date == date(2024, 2, 29)
        assert period.end_date == date(2024, 3, 30)

    def test_period_type_is_monthly(self):
        period = get_current_period(month_start_day="last", as_of=date(2026, 4, 20))
        # Period type is now implicit; verify the BudgetPeriod still has a stable shape.
        assert period.days_in_period == (period.end_date - period.start_date).days + 1


# ---------------------------------------------------------------------------
# navigate_period (monthly only)
# ---------------------------------------------------------------------------

class TestNavigatePeriod:
    def test_monthly_next(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 15))
        next_period = navigate_period(period, direction=1, month_start_day=1)
        assert next_period.start_date == date(2026, 4, 1)
        assert next_period.end_date == date(2026, 4, 30)

    def test_monthly_prev(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 15))
        prev_period = navigate_period(period, direction=-1, month_start_day=1)
        assert prev_period.start_date == date(2026, 2, 1)
        assert prev_period.end_date == date(2026, 2, 28)

    def test_monthly_custom_next(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 15))
        next_period = navigate_period(period, direction=1, month_start_day=15)
        assert next_period.start_date == date(2026, 4, 15)
        assert next_period.end_date == date(2026, 5, 14)

    def test_year_boundary_navigate(self):
        period = get_current_period(month_start_day=1, as_of=date(2025, 12, 15))
        next_period = navigate_period(period, direction=1, month_start_day=1)
        assert next_period.start_date == date(2026, 1, 1)
        assert next_period.end_date == date(2026, 1, 31)

    def test_last_next(self):
        # From Mar 31 → Apr 29 period, next should be Apr 30 → May 30
        period = get_current_period(month_start_day="last", as_of=date(2026, 4, 20))
        nxt = navigate_period(period, direction=1, month_start_day="last")
        assert nxt.start_date == date(2026, 4, 30)
        assert nxt.end_date == date(2026, 5, 30)

    def test_last_prev(self):
        # From Mar 31 → Apr 29 period, prev should be Feb 28 → Mar 30
        period = get_current_period(month_start_day="last", as_of=date(2026, 4, 20))
        prev = navigate_period(period, direction=-1, month_start_day="last")
        assert prev.start_date == date(2026, 2, 28)
        assert prev.end_date == date(2026, 3, 30)


# ---------------------------------------------------------------------------
# days_elapsed semantics
# ---------------------------------------------------------------------------

class TestDaysElapsed:
    def test_past_period_elapsed_equals_full_days(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 15))
        prev = navigate_period(period, direction=-1, month_start_day=1)
        assert prev.start_date == date(2026, 2, 1)
        assert prev.end_date == date(2026, 2, 28)
        assert prev.days_elapsed == 28

    def test_current_period_elapsed_nonzero(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 10))
        assert period.days_elapsed == 10


# ---------------------------------------------------------------------------
# prorate_cap — always returns monthly_cap unchanged for monthly periods
# ---------------------------------------------------------------------------

class TestProratecap:
    def test_calendar_month_no_proration(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 15))
        assert prorate_cap(1000.0, period) == 1000.0

    def test_custom_start_no_proration(self):
        period = get_current_period(month_start_day=15, as_of=date(2026, 3, 15))
        assert prorate_cap(1000.0, period) == 1000.0

    def test_last_day_no_proration(self):
        period = get_current_period(month_start_day="last", as_of=date(2026, 4, 20))
        assert prorate_cap(1000.0, period) == 1000.0

    def test_zero_cap(self):
        period = get_current_period(month_start_day=1, as_of=date(2026, 3, 15))
        assert prorate_cap(0.0, period) == 0.0


# ---------------------------------------------------------------------------
# get_period_containing_date
# ---------------------------------------------------------------------------

class TestGetPeriodContainingDate:
    def test_calendar_month(self):
        period = get_period_containing_date(date(2026, 3, 15), month_start_day=1)
        assert period.start_date == date(2026, 3, 1)
        assert period.end_date == date(2026, 3, 31)

    def test_custom_start(self):
        period = get_period_containing_date(date(2026, 3, 5), month_start_day=15)
        assert period.start_date == date(2026, 2, 15)
        assert period.end_date == date(2026, 3, 14)

    def test_last(self):
        period = get_period_containing_date(date(2026, 4, 20), month_start_day="last")
        assert period.start_date == date(2026, 3, 31)
        assert period.end_date == date(2026, 4, 29)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
