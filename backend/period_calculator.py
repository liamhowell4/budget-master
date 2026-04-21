"""
Period Calculator - Monthly-only budget periods.

Each user's budget runs on a monthly cadence. The only knob is which day of
the month the period starts:
- int 1..28: period starts on that day of each month.
- "last": period starts on the last day of each calendar month (handles 28/29/30/31).

Each period has a unique ID used for alert tracking in Firestore.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange
from typing import Literal, Optional, Union


MonthStartDay = Union[int, Literal["last"]]


@dataclass
class BudgetPeriod:
    start_date: date        # inclusive
    end_date: date          # inclusive
    period_id: str          # unique key for alert tracking
    label: str              # e.g., "Mar 15 – Apr 14" or "March 2026"
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


def _prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


# ---------------------------------------------------------------------------
# Monthly period
# ---------------------------------------------------------------------------

def _get_monthly_period_last_day(as_of: date) -> BudgetPeriod:
    """Period starts on the last day of the previous calendar month and ends
    on the day before the last day of the current calendar month."""
    year = as_of.year
    month = as_of.month

    this_month_last = _days_in_calendar_month(year, month)

    if as_of.day >= this_month_last:
        # Today is the last day of this month — period just started today.
        period_start = date(year, month, this_month_last)
        next_year, next_month = _next_month(year, month)
        next_month_last = _days_in_calendar_month(next_year, next_month)
        period_end = date(next_year, next_month, next_month_last - 1)
    else:
        # Period started on the last day of the previous month.
        prev_year, prev_month = _prev_month(year, month)
        prev_month_last = _days_in_calendar_month(prev_year, prev_month)
        period_start = date(prev_year, prev_month, prev_month_last)
        period_end = date(year, month, this_month_last - 1)

    period_id = f"monthly-{period_start.year}-{period_start.month:02d}-{period_start.day:02d}"
    label = _period_label(period_start, period_end)
    days_in = (period_end - period_start).days + 1
    elapsed = _days_elapsed_in_period(period_start, period_end, as_of)

    return BudgetPeriod(
        start_date=period_start,
        end_date=period_end,
        period_id=period_id,
        label=label,
        days_in_period=days_in,
        days_elapsed=elapsed,
    )


def _get_monthly_period(start_day: MonthStartDay, as_of: date) -> BudgetPeriod:
    """Compute the monthly budget period containing *as_of*."""
    if start_day == "last":
        return _get_monthly_period_last_day(as_of)

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
            next_year, next_month = _next_month(year, month)
            actual_end_day = _clamp_day(next_year, next_month, start_day - 1)
            period_end = date(next_year, next_month, actual_end_day)
        else:
            # Period started last month
            prev_year, prev_month = _prev_month(year, month)
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
        period_id=period_id,
        label=label,
        days_in_period=days_in,
        days_elapsed=elapsed,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _normalize_start_day(month_start_day) -> MonthStartDay:
    """Accept int 1..28 or the string "last"; raise on anything else."""
    if isinstance(month_start_day, str):
        if month_start_day == "last":
            return "last"
        # Tolerate stringified ints for JSON-ish inputs.
        try:
            month_start_day = int(month_start_day)
        except ValueError:
            raise ValueError(
                f"month_start_day must be an int 1-28 or 'last', got {month_start_day!r}"
            )
    if not isinstance(month_start_day, int) or not (1 <= month_start_day <= 28):
        raise ValueError(
            f"month_start_day must be an int 1-28 or 'last', got {month_start_day!r}"
        )
    return month_start_day


def get_current_period(
    month_start_day: MonthStartDay = 1,
    as_of: Optional[date] = None,
) -> BudgetPeriod:
    """Return the monthly budget period that contains *as_of* (defaults to today).

    Args:
        month_start_day: Day of month the period starts — int 1..28 or "last".
        as_of: Date to compute the period for (defaults to today).
    """
    if as_of is None:
        as_of = date.today()
    normalized = _normalize_start_day(month_start_day)
    return _get_monthly_period(normalized, as_of)


def get_period_containing_date(
    target_date: date,
    month_start_day: MonthStartDay = 1,
) -> BudgetPeriod:
    """Return the monthly period that contains *target_date*."""
    return get_current_period(month_start_day=month_start_day, as_of=target_date)


def navigate_period(
    period: BudgetPeriod,
    direction: int = 1,
    month_start_day: MonthStartDay = 1,
) -> BudgetPeriod:
    """Return the adjacent monthly period.

    Args:
        period: The reference period.
        direction: +1 for next period, -1 for previous.
        month_start_day: Same start-day value used to construct the reference period.
    """
    if direction > 0:
        reference_date = period.end_date + timedelta(days=1)
    else:
        reference_date = period.start_date - timedelta(days=1)
    return get_current_period(month_start_day=month_start_day, as_of=reference_date)


def prorate_cap(monthly_cap: float, period: BudgetPeriod) -> float:
    """Return the cap for a given monthly period.

    Monthly periods are never prorated — they always span ~one calendar month,
    so the cap applies in full.
    """
    return monthly_cap
