"""
Test script for recurring expense detection.
Run this to test the AI detection without needing to send SMS.

Usage:
    python test_recurring_detection.py
"""

from backend.expense_parser import detect_recurring

# Test cases
test_inputs = [
    "Recurring: rent monthly on the 1st, 1400",
    "recurring rent $1000 monthly on the 1st",
    "netflix subscription $15 monthly",
    "coffee $5",  # Should NOT be recurring
    "gym membership $50 every month on the 15th",
    "rent 1500 monthly 1st",
]

print("="*80)
print("TESTING RECURRING EXPENSE DETECTION")
print("="*80)

for i, text in enumerate(test_inputs, 1):
    print(f"\n{'='*80}")
    print(f"Test {i}: '{text}'")
    print(f"{'='*80}")

    try:
        result = detect_recurring(text)

        print(f"\n✅ RESULT:")
        print(f"   is_recurring: {result.is_recurring}")
        print(f"   confidence: {result.confidence}")
        print(f"   explanation: {result.explanation}")

        if result.recurring_expense:
            rec = result.recurring_expense
            print(f"\n📋 PARSED EXPENSE:")
            print(f"   expense_name: {rec.expense_name}")
            print(f"   amount: ${rec.amount:.2f}")
            print(f"   category: {rec.category.name}")
            print(f"   frequency: {rec.frequency.value}")
            print(f"   day_of_month: {rec.day_of_month}")
            print(f"   day_of_week: {rec.day_of_week}")
            print(f"   last_of_month: {rec.last_of_month}")
        else:
            print(f"\n❌ No recurring expense parsed")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("TESTING COMPLETE")
print("="*80)
