"""
Period Calculator - Flexible budget period support.

Supports monthly (calendar or custom start-day), weekly, and biweekly periods.
Each period has a unique ID used for alert tracking in Firestore.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange
from typing import Optional


@dataclass
class BudgetPeriod:
    start_date: date        # inclusive
    end_date: date          # inclusive
    period_type: str        # "monthly" | "weekly" | "biweekly"
    period_id: str          # unique key for alert tracking
    label: str              # e.g., "Mar 15 – Apr 14" or "Mar 3 – Mar 9"
    days_in_period: int
    days_elapsed: int       # 0 if viewing historical period


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _days_in_calendar_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def _clamp_day(year: int, month: int, day: int) -> int:
    """Clamp day to the last valid day in the given month."""
    return min(day, _days_in_calendar_month(year, month))


def _period_label(start: date, end: date) -> str:
    if start.month == end.month and start.year == end.year:
        return f"{start.strftime('%b')} {start.day} – {end.day}"
    return f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}"


def _days_elapsed_in_period(start: date, end: date, as_of: date) -> int:
    """Return days elapsed in the period as of *as_of* date.

    Returns 0 for historical periods (as_of is after the period ends).
    """
    if as_of > end:
        return 0
    if as_of < start:
        return 0
    return (as_of - start).days + 1  # +1 because start day counts as day 1


# ---------------------------------------------------------------------------
# Monthly period
# ---------------------------------------------------------------------------

def _get_monthly_period(start_day: int, as_of: date) -> BudgetPeriod:
    """Compute the monthly budget period containing *as_of*.

    When start_day == 1 the period is simply the calendar month.
    When start_day > 1 the period spans from this month/start_day to the day
    before start_day in the next month (or prev month / start_day to this
    month / start_day - 1 when today is before start_day).
    """
    year = as_of.year
    month = as_of.month

    if start_day == 1:
        # Standard calendar month
        period_start = date(year, month, 1)
        last_day = _days_in_calendar_month(year, month)
        period_end = date(year, month, last_day)
        period_id = f"monthly-{year}-{month:02d}-01"
        label = period_start.strftime("%B %Y")
    else:
        if as_of.day >= start_day:
            # Period starts this month
            actual_start_day = _clamp_day(year, month, start_day)
            period_start = date(year, month, actual_start_day)

            # End is the day before start_day in next month
            if month == 12:
                next_year, next_month = year + 1, 1
            else:
                next_year, next_month = year, month + 1
            actual_end_day = _clamp_day(next_year, next_month, start_day - 1)
            period_end = date(next_year, next_month, actual_end_day)
        else:
            # Period started last month
            if month == 1:
                prev_year, prev_month = year - 1, 12
            else:
                prev_year, prev_month = year, month - 1
            actual_start_day = _clamp_day(prev_year, prev_month, start_day)
            period_start = date(prev_year, prev_month, actual_start_day)

            actual_end_day = _clamp_day(year, month, start_day - 1)
            period_end = date(year, month, actual_end_day)

        period_id = f"monthly-{period_start.year}-{period_start.month:02d}-{period_start.day:02d}"
        label = _period_label(period_start, period_end)

    days_in = (period_end - period_start).days + 1
    elapsed = _days_elapsed_in_period(period_start, period_end, as_of)

    return BudgetPeriod(
        start_date=period_start,
        end_date=period_end,
        period_type="monthly",
        period_id=period_id,
        label=label,
        days_in_period=days_in,
        days_elapsed=elapsed,
    )


# ---------------------------------------------------------------------------
# Weekly period
# ---------------------------------------------------------------------------

_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Python weekday(): Monday=0, ..., Sunday=6
_WEEKDAY_MAP = {name: i for i, name in enumerate(_WEEKDAY_NAMES)}


def _get_weekly_period(week_start_day: str, as_of: date) -> BudgetPeriod:
    """Compute the 7-day period containing *as_of* that starts on *week_start_day*."""
    target_weekday = _WEEKDAY_MAP.get(week_start_day, 0)  # default Monday
    days_since_start = (as_of.weekday() - target_weekday) % 7
    period_start = as_of - timedelta(days=days_since_start)
    period_end = period_start + timedelta(days=6)

    period_id = f"weekly-{period_start.year}-{period_start.month:02d}-{period_start.day:02d}"
    label = _period_label(period_start, period_end)
    elapsed = _days_elapsed_in_period(period_start, period_end, as_of)

    return BudgetPeriod(
        start_date=period_start,
        end_date=period_end,
        period_type="weekly",
        period_id=period_id,
        label=label,
        days_in_period=7,
        days_elapsed=elapsed,
    )


# ---------------------------------------------------------------------------
# Biweekly period
# ---------------------------------------------------------------------------

def _parse_anchor(anchor: str) -> date:
    """Parse anchor date string 'YYYY-MM-DD' to date object."""
    parts = anchor.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def _get_biweekly_period(anchor: str, as_of: date) -> BudgetPeriod:
    """Compute the 14-day period containing *as_of* anchored at *anchor* date."""
    anchor_date = _parse_anchor(anchor)
    delta_days = (as_of - anchor_date).days
    period_num = math.floor(delta_days / 14)
    period_start = anchor_date + timedelta(days=period_num * 14)
    period_end = period_start + timedelta(days=13)

    period_id = f"biweekly-{period_start.year}-{period_start.month:02d}-{period_start.day:02d}"
    label = _period_label(period_start, period_end)
    elapsed = _days_elapsed_in_period(period_start, period_end, as_of)

    return BudgetPeriod(
        start_date=period_start,
        end_date=period_end,
        period_type="biweekly",
        period_id=period_id,
        label=label,
        days_in_period=14,
        days_elapsed=elapsed,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_period(
    period_type: str = "monthly",
    month_start_day: int = 1,
    week_start_day: str = "Monday",
    biweekly_anchor: str = "2024-01-01",
    as_of: Optional[date] = None,
) -> BudgetPeriod:
    """Return the budget period that contains *as_of* (defaults to today).

    Args:
        period_type: "monthly", "weekly", or "biweekly"
        month_start_day: Day of month the monthly period starts (1–28). Only used for "monthly".
        week_start_day: Weekday name the weekly period starts on. Only used for "weekly".
        biweekly_anchor: ISO date string "YYYY-MM-DD" for a known biweekly period start.
        as_of: Date to compute the period for (defaults to today).

    Returns:
        BudgetPeriod for the current period.
    """
    if as_of is None:
        as_of = date.today()

    if period_type == "weekly":
        return _get_weekly_period(week_start_day, as_of)
    elif period_type == "biweekly":
        return _get_biweekly_period(biweekly_anchor, as_of)
    else:
        return _get_monthly_period(month_start_day, as_of)


def get_period_containing_date(
    target_date: date,
    period_type: str = "monthly",
    month_start_day: int = 1,
    week_start_day: str = "Monday",
    biweekly_anchor: str = "2024-01-01",
) -> BudgetPeriod:
    """Return the period that contains *target_date*."""
    return get_current_period(
        period_type=period_type,
        month_start_day=month_start_day,
        week_start_day=week_start_day,
        biweekly_anchor=biweekly_anchor,
        as_of=target_date,
    )


def navigate_period(
    period: BudgetPeriod,
    direction: int = 1,
    month_start_day: int = 1,
    week_start_day: str = "Monday",
    biweekly_anchor: str = "2024-01-01",
) -> BudgetPeriod:
    """Return the adjacent period.

    Args:
        period: The reference period.
        direction: +1 for next period, -1 for previous.
        month_start_day, week_start_day, biweekly_anchor: Same params used to
            construct the reference period.

    Returns:
        The neighboring BudgetPeriod.
    """
    if direction > 0:
        # Step one day past the end of the current period
        reference_date = period.end_date + timedelta(days=1)
    else:
        # Step one day before the start of the current period
        reference_date = period.start_date - timedelta(days=1)

    return get_current_period(
        period_type=period.period_type,
        month_start_day=month_start_day,
        week_start_day=week_start_day,
        biweekly_anchor=biweekly_anchor,
        as_of=reference_date,
    )


def prorate_cap(monthly_cap: float, period: BudgetPeriod) -> float:
    """Return the prorated cap for a given period.

    For monthly periods with start_day == 1 the factor is always 1.0 (backward compat).
    For all other period types, the factor is days_in_period / days_in_calendar_month.
    The reference calendar month is the month that contains the period's start_date.

    Args:
        monthly_cap: The full monthly budget cap.
        period: The BudgetPeriod to prorate for.

    Returns:
        Prorated cap (float).
    """
    if period.period_type == "monthly":
        # Standard calendar-month period (or close enough) — no proration
        return monthly_cap

    # Determine the reference calendar month from the period start
    ref_year = period.start_date.year
    ref_month = period.start_date.month
    days_in_month = _days_in_calendar_month(ref_year, ref_month)

    factor = period.days_in_period / days_in_month
    return monthly_cap * factor
