"""
Seed Firestore Script - Initialize categories and budget_caps collections.

Run this script once during initial setup:
    python scripts/seed_firestore.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.firebase_client import FirebaseClient
from backend.output_schemas import ExpenseType


def seed_categories(client: FirebaseClient):
    """Seed the categories collection from ExpenseType enum."""
    print("🌱 Seeding categories collection...")
    client.seed_categories()


def seed_budget_caps(client: FirebaseClient):
    """
    Seed default budget caps.

    Adjust these values based on your personal budget needs.
    """
    print("🌱 Seeding budget_caps collection...")

    # Default monthly budget caps (in dollars)
    default_caps = {
        "FOOD_OUT": 525.00,      # Dining out
        "RENT": 1400.00,         # Apartment rent
        "UTILITIES": 200.00,     # Electricity, water, internet
        "MEDICAL": 25.00,        # Doctor, dentist, prescriptions
        "GAS": 50.00,            # Gasoline for car
        "GROCERIES": 400.00,     # Grocery shopping
        "RIDE_SHARE": 100.00,    # Uber/Lyft/taxi
        "COFFEE": 50.00,         # Coffee shops
        "HOTEL": 0.00,           # Hotels (travel - set when needed)
        "TECH": 50.00,           # Software subscriptions, AI tools
        "TRAVEL": 200.00,        # Airfare, rental cars, travel fees
        "OTHER": 200.00,         # Miscellaneous
        "TOTAL": 3200.00         # Total
    }

    for category, amount in default_caps.items():
        client.set_budget_cap(category, amount)
        print(f"  ✅ Set {category}: ${amount:.2f}/month")

    print(f"✅ Seeded {len(default_caps)} budget caps")


def add_sample_expenses(client: FirebaseClient):
    """
    Add sample expenses for testing (optional).
    Uncomment the expenses you want to add.
    """
    print("🌱 Adding sample expenses...")

    from datetime import date
    from output_schemas import Expense, Date

    # Sample expenses
    samples = [
        Expense(
            expense_name="Chipotle lunch",
            amount=15.50,
            date=Date(day=date.today().day, month=date.today().month, year=date.today().year),
            category=ExpenseType.FOOD_OUT
        ),
        Expense(
            expense_name="Starbucks coffee",
            amount=5.25,
            date=Date(day=date.today().day, month=date.today().month, year=date.today().year),
            category=ExpenseType.COFFEE
        ),
        Expense(
            expense_name="Safeway groceries",
            amount=87.42,
            date=Date(day=date.today().day, month=date.today().month, year=date.today().year),
            category=ExpenseType.GROCERIES
        ),
    ]

    for expense in samples:
        expense_id = client.save_expense(expense, input_type="sample")
        print(f"  ✅ Added: {expense.expense_name} (${expense.amount:.2f}) - ID: {expense_id}")

    print(f"✅ Added {len(samples)} sample expenses")


def main():
    """Main function to seed Firestore collections."""
    print("=" * 60)
    print("🚀 Firestore Seeding Script")
    print("=" * 60)
    print()

    # Initialize Firebase client
    try:
        client = FirebaseClient()
        print("✅ Connected to Firebase")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to Firebase: {e}")
        print("Make sure FIREBASE_KEY is set in your .env file")
        return

    # Seed collections
    try:
        # 1. Seed categories
        seed_categories(client)
        print()

        # 2. Seed budget caps
        seed_budget_caps(client)
        print()

        # 3. (Optional) Add sample expenses
        # Uncomment the line below to add sample expenses
        # add_sample_expenses(client)
        # print()

        print("=" * 60)
        print("✅ Seeding complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Check your Firestore console to verify the data")
        print("2. Adjust budget caps by running:")
        print("   python -c 'from firebase_client import FirebaseClient; ")
        print("   client = FirebaseClient(); client.set_budget_cap(\"FOOD_OUT\", 500.00)'")
        print("3. Start the FastAPI server: uvicorn api:app --reload")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
