"""
Test script for BudgetManager to verify budget calculations and warnings.
"""

from datetime import datetime
from budget_manager import BudgetManager
from output_schemas import ExpenseType

def test_budget_warnings():
    """Test budget warning generation at different thresholds."""

    budget_manager = BudgetManager()

    # Use current date for testing
    now = datetime.now()
    year = now.year
    month = now.month

    print("=" * 60)
    print("BUDGET MANAGER TEST")
    print("=" * 60)
    print(f"Testing for: {year}-{month:02d}\n")

    # Test 1: Small coffee expense (should be well under budget)
    print("Test 1: $5 Coffee expense")
    print("-" * 60)
    warning = budget_manager.get_budget_warning(
        category=ExpenseType.COFFEE,
        amount=5.0,
        year=year,
        month=month
    )
    if warning:
        print(warning)
    else:
        print("✅ No warnings (under 50% threshold)")
    print()

    # Test 2: Larger expense to trigger 50% warning
    print("Test 2: $25 Coffee expense (should hit 50% threshold)")
    print("-" * 60)
    warning = budget_manager.get_budget_warning(
        category=ExpenseType.COFFEE,
        amount=25.0,
        year=year,
        month=month
    )
    print(warning if warning else "No warnings")
    print()

    # Test 3: Large FOOD_OUT expense
    print("Test 3: $500 FOOD_OUT expense (should hit 90%+ threshold)")
    print("-" * 60)
    warning = budget_manager.get_budget_warning(
        category=ExpenseType.FOOD_OUT,
        amount=500.0,
        year=year,
        month=month
    )
    print(warning if warning else "No warnings")
    print()

    # Test 4: Huge expense to trigger OVER BUDGET
    print("Test 4: $5000 OTHER expense (should trigger OVER BUDGET)")
    print("-" * 60)
    warning = budget_manager.get_budget_warning(
        category=ExpenseType.OTHER,
        amount=5000.0,
        year=year,
        month=month
    )
    print(warning if warning else "No warnings")
    print()

    # Test 5: Check current spending totals
    print("Test 5: Current spending summary")
    print("-" * 60)
    total_spending = budget_manager.calculate_total_monthly_spending(year, month)
    print(f"Total spending this month: ${total_spending:.2f}")

    coffee_spending = budget_manager.calculate_monthly_spending(ExpenseType.COFFEE, year, month)
    print(f"Coffee spending this month: ${coffee_spending:.2f}")

    food_spending = budget_manager.calculate_monthly_spending(ExpenseType.FOOD_OUT, year, month)
    print(f"Food out spending this month: ${food_spending:.2f}")
    print()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_budget_warnings()
