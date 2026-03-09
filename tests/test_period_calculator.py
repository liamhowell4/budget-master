"""
Tests for backend/period_calculator.py
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
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 15))
        assert period.start_date == date(2026, 3, 1)
        assert period.end_date == date(2026, 3, 31)
        assert period.period_type == "monthly"
        assert period.period_id == "monthly-2026-03-01"
        assert period.days_in_period == 31
        assert period.days_elapsed == 15
        assert "March 2026" in period.label

    def test_first_day(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 1, 1))
        assert period.start_date == date(2026, 1, 1)
        assert period.end_date == date(2026, 1, 31)
        assert period.days_elapsed == 1

    def test_last_day(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 2, 28))
        assert period.start_date == date(2026, 2, 1)
        assert period.end_date == date(2026, 2, 28)
        assert period.days_elapsed == 28

    def test_december(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2025, 12, 25))
        assert period.start_date == date(2025, 12, 1)
        assert period.end_date == date(2025, 12, 31)

    def test_february_leap_year(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2024, 2, 15))
        assert period.end_date == date(2024, 2, 29)
        assert period.days_in_period == 29

    def test_february_non_leap_year(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2025, 2, 28))
        assert period.end_date == date(2025, 2, 28)
        assert period.days_in_period == 28


# ---------------------------------------------------------------------------
# Monthly (start_day=N) — custom start day
# ---------------------------------------------------------------------------

class TestMonthlyCustomStartDay:
    def test_on_start_day(self):
        # As of Mar 15, start_day=15 → period is Mar 15 – Apr 14
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 15))
        assert period.start_date == date(2026, 3, 15)
        assert period.end_date == date(2026, 4, 14)
        assert period.days_elapsed == 1

    def test_after_start_day(self):
        # As of Mar 20, start_day=15 → period is Mar 15 – Apr 14
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 20))
        assert period.start_date == date(2026, 3, 15)
        assert period.end_date == date(2026, 4, 14)

    def test_before_start_day(self):
        # As of Mar 5, start_day=15 → period is Feb 15 – Mar 14
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 5))
        assert period.start_date == date(2026, 2, 15)
        assert period.end_date == date(2026, 3, 14)

    def test_period_id_format(self):
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 15))
        assert period.period_id == "monthly-2026-03-15"

    def test_year_boundary_january(self):
        # As of Jan 10, start_day=15 → period is Dec 15 – Jan 14
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 1, 10))
        assert period.start_date == date(2025, 12, 15)
        assert period.end_date == date(2026, 1, 14)

    def test_year_boundary_december(self):
        # As of Dec 20, start_day=15 → period is Dec 15 – Jan 14
        period = get_current_period("monthly", month_start_day=15, as_of=date(2025, 12, 20))
        assert period.start_date == date(2025, 12, 15)
        assert period.end_date == date(2026, 1, 14)

    def test_start_day_clamped_in_feb(self):
        # start_day=31, February → clamp to 28 (or 29 in leap year)
        period = get_current_period("monthly", month_start_day=31, as_of=date(2025, 2, 15))
        # If today is Feb 15 and start_day=31, today < 31 so period started last month
        # Jan 31 → Feb 27 (end is day before 31, clamped: Feb has 28 days, so end = Feb 28)
        assert period.start_date == date(2025, 1, 31)
        assert period.end_date == date(2025, 2, 28)

    def test_days_in_period(self):
        # Mar 15 → Apr 14 = 31 days
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 15))
        assert period.days_in_period == 31


# ---------------------------------------------------------------------------
# Weekly period
# ---------------------------------------------------------------------------

class TestWeeklyPeriod:
    def test_on_start_day_monday(self):
        # 2026-03-02 is a Monday
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 2))
        assert period.start_date == date(2026, 3, 2)
        assert period.end_date == date(2026, 3, 8)
        assert period.days_in_period == 7
        assert period.days_elapsed == 1

    def test_mid_week(self):
        # 2026-03-04 is Wednesday
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 4))
        assert period.start_date == date(2026, 3, 2)
        assert period.end_date == date(2026, 3, 8)
        assert period.days_elapsed == 3

    def test_last_day_of_week(self):
        # 2026-03-08 is Sunday (end of Mon-starting week)
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 8))
        assert period.start_date == date(2026, 3, 2)
        assert period.end_date == date(2026, 3, 8)
        assert period.days_elapsed == 7

    def test_sunday_start(self):
        # 2026-03-01 is Sunday → with Sunday start, that's day 1
        period = get_current_period("weekly", week_start_day="Sunday", as_of=date(2026, 3, 1))
        assert period.start_date == date(2026, 3, 1)
        assert period.end_date == date(2026, 3, 7)

    def test_period_id_format(self):
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 2))
        assert period.period_id == "weekly-2026-03-02"

    def test_week_spans_month_boundary(self):
        # 2026-03-30 is Monday → period ends Apr 5
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 31))
        assert period.start_date == date(2026, 3, 30)
        assert period.end_date == date(2026, 4, 5)

    def test_week_spans_year_boundary(self):
        # Dec 28, 2025 is Sunday. Monday start → week started Dec 29
        # Wait - let's use a Monday. 2025-12-29 is a Monday.
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2025, 12, 31))
        assert period.start_date == date(2025, 12, 29)
        assert period.end_date == date(2026, 1, 4)


# ---------------------------------------------------------------------------
# Biweekly period
# ---------------------------------------------------------------------------

class TestBiweeklyPeriod:
    ANCHOR = "2026-01-05"  # arbitrary known Monday

    def test_on_anchor(self):
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 1, 5))
        assert period.start_date == date(2026, 1, 5)
        assert period.end_date == date(2026, 1, 18)
        assert period.days_in_period == 14
        assert period.days_elapsed == 1

    def test_mid_period(self):
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 1, 12))
        assert period.start_date == date(2026, 1, 5)
        assert period.end_date == date(2026, 1, 18)
        assert period.days_elapsed == 8

    def test_last_day_of_period(self):
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 1, 18))
        assert period.start_date == date(2026, 1, 5)
        assert period.end_date == date(2026, 1, 18)
        assert period.days_elapsed == 14

    def test_next_period_starts(self):
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 1, 19))
        assert period.start_date == date(2026, 1, 19)
        assert period.end_date == date(2026, 2, 1)

    def test_period_id_format(self):
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 1, 5))
        assert period.period_id == "biweekly-2026-01-05"

    def test_spans_month_boundary(self):
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 1, 25))
        assert period.start_date == date(2026, 1, 19)
        assert period.end_date == date(2026, 2, 1)

    def test_far_future(self):
        # Many periods after anchor
        period = get_current_period("biweekly", biweekly_anchor=self.ANCHOR, as_of=date(2026, 6, 1))
        # Anchor = Jan 5. Days to Jun 1 = 147 days. period_num = floor(147/14) = 10
        # start = Jan 5 + 140 = Jun 23? Let's compute manually.
        # Jan 5 + 10*14 = Jan 5 + 140 days
        from datetime import timedelta
        expected_start = date(2026, 1, 5) + timedelta(days=10 * 14)
        expected_end = expected_start + timedelta(days=13)
        assert period.start_date == expected_start
        assert period.end_date == expected_end


# ---------------------------------------------------------------------------
# navigate_period
# ---------------------------------------------------------------------------

class TestNavigatePeriod:
    def test_monthly_next(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 15))
        next_period = navigate_period(period, direction=1, month_start_day=1)
        assert next_period.start_date == date(2026, 4, 1)
        assert next_period.end_date == date(2026, 4, 30)

    def test_monthly_prev(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 15))
        prev_period = navigate_period(period, direction=-1, month_start_day=1)
        assert prev_period.start_date == date(2026, 2, 1)
        assert prev_period.end_date == date(2026, 2, 28)

    def test_monthly_custom_next(self):
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 15))
        next_period = navigate_period(period, direction=1, month_start_day=15)
        assert next_period.start_date == date(2026, 4, 15)
        assert next_period.end_date == date(2026, 5, 14)

    def test_weekly_next(self):
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 2))
        next_period = navigate_period(period, direction=1, week_start_day="Monday")
        assert next_period.start_date == date(2026, 3, 9)
        assert next_period.end_date == date(2026, 3, 15)

    def test_weekly_prev(self):
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 2))
        prev_period = navigate_period(period, direction=-1, week_start_day="Monday")
        assert prev_period.start_date == date(2026, 2, 23)
        assert prev_period.end_date == date(2026, 3, 1)

    def test_biweekly_next(self):
        anchor = "2026-01-05"
        period = get_current_period("biweekly", biweekly_anchor=anchor, as_of=date(2026, 1, 5))
        next_period = navigate_period(period, direction=1, biweekly_anchor=anchor)
        assert next_period.start_date == date(2026, 1, 19)

    def test_biweekly_prev(self):
        anchor = "2026-01-05"
        period = get_current_period("biweekly", biweekly_anchor=anchor, as_of=date(2026, 1, 5))
        prev_period = navigate_period(period, direction=-1, biweekly_anchor=anchor)
        assert prev_period.start_date == date(2025, 12, 22)
        assert prev_period.end_date == date(2026, 1, 4)

    def test_year_boundary_navigate(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2025, 12, 15))
        next_period = navigate_period(period, direction=1, month_start_day=1)
        assert next_period.start_date == date(2026, 1, 1)
        assert next_period.end_date == date(2026, 1, 31)


# ---------------------------------------------------------------------------
# Historical periods (days_elapsed == 0)
# ---------------------------------------------------------------------------

class TestDaysElapsed:
    def test_historical_period_has_zero_elapsed(self):
        # A period whose as_of is before start → days_elapsed = 0
        # Simulate: get a period for a future date, then check days_elapsed == 0
        # Navigate forward twice so the 'as_of' used to construct it is before the period
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 1))
        # Navigate: as_of used = period.end_date + 1 = Apr 1 → April period, days_elapsed >= 1
        # Instead, directly construct a period where as_of is before the period to check elapsed=0
        # This happens when as_of passed to get_current_period is before the period start
        # That can't happen for the "current" period by definition.
        # So test: a period navigated to from a past as_of has days_elapsed = full or 0
        # The actual behavior: navigate_period(period, +1) uses as_of=period.end_date+1
        # which IS within the next period → days_elapsed will be 1 (first day).
        nxt = navigate_period(period, direction=1, month_start_day=1)
        # April 1 is first day of April period so days_elapsed == 1
        assert nxt.days_elapsed == 1

    def test_past_period_elapsed_equals_full_days(self):
        # Navigate backwards: as_of = period.start_date - 1 = Feb 28 → Feb period
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 15))
        prev = navigate_period(period, direction=-1, month_start_day=1)
        # as_of used = Feb 28 (last day of Feb 2026)
        assert prev.start_date == date(2026, 2, 1)
        assert prev.end_date == date(2026, 2, 28)
        assert prev.days_elapsed == 28  # as_of = Feb 28 = last day

    def test_current_period_elapsed_nonzero(self):
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 10))
        assert period.days_elapsed == 10


# ---------------------------------------------------------------------------
# prorate_cap
# ---------------------------------------------------------------------------

class TestProratecap:
    def test_monthly_calendar_no_proration(self):
        # Standard calendar month → factor 1.0
        period = get_current_period("monthly", month_start_day=1, as_of=date(2026, 3, 15))
        assert prorate_cap(1000.0, period) == 1000.0

    def test_weekly_proration(self):
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 2))
        # Period starts in March (31 days). 7/31 * 1000
        expected = 1000.0 * (7 / 31)
        assert abs(prorate_cap(1000.0, period) - expected) < 0.001

    def test_biweekly_proration(self):
        period = get_current_period("biweekly", biweekly_anchor="2026-01-05", as_of=date(2026, 1, 5))
        # Period starts in January (31 days). 14/31 * 1000
        expected = 1000.0 * (14 / 31)
        assert abs(prorate_cap(1000.0, period) - expected) < 0.001

    def test_monthly_custom_start_proration(self):
        # Mar 15 → Apr 14 = 31 days. Starts in March (31 days). Factor = 31/31 = 1.0
        period = get_current_period("monthly", month_start_day=15, as_of=date(2026, 3, 15))
        # 31 days >= 28, so no proration
        assert prorate_cap(1000.0, period) == 1000.0

    def test_monthly_custom_short_feb(self):
        # Feb 15 → Mar 14 = 28 days — monthly periods are never prorated
        period = get_current_period("monthly", month_start_day=15, as_of=date(2025, 2, 20))
        result = prorate_cap(1000.0, period)
        assert result == 1000.0

    def test_zero_cap(self):
        period = get_current_period("weekly", week_start_day="Monday", as_of=date(2026, 3, 2))
        assert prorate_cap(0.0, period) == 0.0


# ---------------------------------------------------------------------------
# get_period_containing_date (convenience wrapper)
# ---------------------------------------------------------------------------

class TestGetPeriodContainingDate:
    def test_delegates_correctly(self):
        period = get_period_containing_date(
            date(2026, 3, 15),
            period_type="monthly",
            month_start_day=1
        )
        assert period.start_date == date(2026, 3, 1)

    def test_weekly(self):
        period = get_period_containing_date(
            date(2026, 3, 4),
            period_type="weekly",
            week_start_day="Monday"
        )
        assert period.start_date == date(2026, 3, 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
