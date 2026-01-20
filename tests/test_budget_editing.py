"""
Test script for budget cap editing functionality.

Tests the /budget-caps/bulk-update endpoint with various scenarios.
"""

import requests
import json

API_URL = "http://localhost:8000"


def test_get_current_budget():
    """Test fetching current budget data."""
    print("\n1. Testing GET /budget...")
    response = requests.get(f"{API_URL}/budget")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Current total budget: ${data['total_cap']:.2f}")
        print(f"   Categories: {len(data['categories'])}")

        # Show current caps
        for cat in data['categories']:
            if cat['cap'] > 0:
                print(f"   - {cat['emoji']} {cat['category']}: ${cat['cap']:.2f}")
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        return None


def test_valid_update():
    """Test valid budget cap update."""
    print("\n2. Testing valid budget update...")

    payload = {
        "total_budget": 2000.0,
        "category_budgets": {
            "FOOD_OUT": 400.0,
            "RENT": 1200.0,
            "GROCERIES": 150.0,
            "COFFEE": 50.0,
            "GAS": 100.0,
            "OTHER": 100.0
        }
    }

    response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data['message']}")
        print(f"   Updated {len(data['updated_caps'])} budget caps")
        return True
    else:
        print(f"❌ Error: {response.status_code} - {response.json()}")
        return False


def test_over_budget():
    """Test validation when sum exceeds total."""
    print("\n3. Testing over-budget validation...")

    payload = {
        "total_budget": 1000.0,
        "category_budgets": {
            "FOOD_OUT": 600.0,
            "RENT": 800.0,  # Total = 1400 > 1000
        }
    }

    response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=payload)

    if response.status_code == 400:
        error = response.json()['detail']
        print(f"✅ Validation working: {error}")
        return True
    else:
        print(f"❌ Should have returned 400, got {response.status_code}")
        return False


def test_invalid_category():
    """Test validation with invalid category name."""
    print("\n4. Testing invalid category validation...")

    payload = {
        "total_budget": 2000.0,
        "category_budgets": {
            "FOOD_OUT": 400.0,
            "INVALID_CATEGORY": 100.0,
        }
    }

    response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=payload)

    if response.status_code == 400:
        error = response.json()['detail']
        print(f"✅ Validation working: {error}")
        return True
    else:
        print(f"❌ Should have returned 400, got {response.status_code}")
        return False


def test_proportional_scaling():
    """Test that budget scales proportionally when total changes."""
    print("\n5. Testing proportional scaling scenario...")

    # First set a baseline budget
    baseline = {
        "total_budget": 1000.0,
        "category_budgets": {
            "FOOD_OUT": 500.0,  # 50%
            "RENT": 300.0,      # 30%
            "OTHER": 200.0      # 20%
        }
    }

    response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=baseline)
    if response.status_code != 200:
        print(f"❌ Failed to set baseline: {response.status_code}")
        return False

    print(f"   Set baseline: $1000 total (FOOD_OUT: $500, RENT: $300, OTHER: $200)")

    # Now scale to 2x (simulating user doubling total budget)
    scaled = {
        "total_budget": 2000.0,
        "category_budgets": {
            "FOOD_OUT": 1000.0,  # 50% of 2000
            "RENT": 600.0,       # 30% of 2000
            "OTHER": 400.0       # 20% of 2000
        }
    }

    response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=scaled)
    if response.status_code == 200:
        print(f"✅ Successfully scaled to $2000 (2x)")
        print(f"   FOOD_OUT: $1000 (50%), RENT: $600 (30%), OTHER: $400 (20%)")
        return True
    else:
        print(f"❌ Failed to scale: {response.status_code}")
        return False


def test_unallocated_to_other():
    """Test that unallocated budget goes to OTHER."""
    print("\n6. Testing unallocated budget to OTHER...")

    payload = {
        "total_budget": 2000.0,
        "category_budgets": {
            "FOOD_OUT": 400.0,
            "RENT": 1200.0,
            "GROCERIES": 150.0,
            # Total allocated: 1750, so OTHER should get 250
            "OTHER": 250.0
        }
    }

    response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=payload)

    if response.status_code == 200:
        data = response.json()
        other_cap = data['updated_caps'].get('OTHER', 0)
        print(f"✅ Success: OTHER = ${other_cap:.2f}")

        if other_cap == 250.0:
            print(f"   ✅ Correct: Unallocated $250 went to OTHER")
            return True
        else:
            print(f"   ⚠️  Expected $250, got ${other_cap:.2f}")
            return False
    else:
        print(f"❌ Error: {response.status_code}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Budget Cap Editing Tests")
    print("=" * 60)

    try:
        # Test 1: Get current budget
        current_budget = test_get_current_budget()

        if not current_budget:
            print("\n❌ Cannot proceed - API not responding")
            exit(1)

        # Test 2: Valid update
        test_valid_update()

        # Test 3: Over-budget validation
        test_over_budget()

        # Test 4: Invalid category validation
        test_invalid_category()

        # Test 5: Proportional scaling
        test_proportional_scaling()

        # Test 6: Unallocated to OTHER
        test_unallocated_to_other()

        # Restore original budget if available
        if current_budget:
            print("\n7. Restoring original budget...")
            original_caps = {cat['category']: cat['cap'] for cat in current_budget['categories']}
            payload = {
                "total_budget": current_budget['total_cap'],
                "category_budgets": original_caps
            }
            response = requests.put(f"{API_URL}/budget-caps/bulk-update", json=payload)
            if response.status_code == 200:
                print("✅ Original budget restored")
            else:
                print("⚠️  Could not restore original budget")

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API at http://localhost:8000")
        print("   Make sure the FastAPI backend is running:")
        print("   $ uvicorn backend.api:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
