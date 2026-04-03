"""
Tests for POST /expenses endpoint.

Runs against the Firestore emulator (FIRESTORE_EMULATOR_HOST=localhost:8080).
Auth is bypassed via FastAPI dependency override.
"""

import os
import sys
from calendar import monthrange
from datetime import datetime

import pytest

# Point at the Firestore emulator before importing anything Firebase-related
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

sys.path.insert(0, str(__file__ + "/../../"))

from fastapi.testclient import TestClient

from backend.api import app
from backend.auth import get_current_user, AuthenticatedUser

TEST_UID = "test-user-create-expense"

def override_auth():
    return AuthenticatedUser(uid=TEST_UID, email="test@example.com", email_verified=True)

app.dependency_overrides[get_current_user] = override_auth

client = TestClient(app)


def _today_dict():
    now = datetime.now()
    return {"day": now.day, "month": now.month, "year": now.year}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_expenses_for_test_user():
    """Fetch current month expenses for the test user."""
    now = datetime.now()
    resp = client.get(f"/expenses?year={now.year}&month={now.month}")
    assert resp.status_code == 200
    return resp.json()["expenses"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_expense_success():
    """POST /expenses returns 200 with a valid expense_id."""
    payload = {
        "expense_name": "Test Coffee",
        "amount": 4.75,
        "category": "COFFEE",
        "date": _today_dict(),
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["expense_id"], str)
    assert len(data["expense_id"]) > 0


def test_create_expense_persisted_in_firestore():
    """Expense created via POST /expenses appears in GET /expenses."""
    before = get_expenses_for_test_user()
    before_ids = {e["id"] for e in before}

    payload = {
        "expense_name": "Test Groceries",
        "amount": 52.30,
        "category": "GROCERIES",
        "date": _today_dict(),
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["expense_id"]

    after = get_expenses_for_test_user()
    after_ids = {e["id"] for e in after}
    assert new_id in after_ids, "Created expense not found in GET /expenses"

    created = next(e for e in after if e["id"] == new_id)
    assert created["expense_name"] == "Test Groceries"
    assert created["amount"] == 52.30
    assert created["category"] == "GROCERIES"


def test_create_expense_custom_date():
    """Date fields are stored as provided, not defaulted to today."""
    date = {"day": 1, "month": 1, "year": 2026}
    payload = {
        "expense_name": "New Year Dinner",
        "amount": 80.00,
        "category": "FOOD_OUT",
        "date": date,
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["expense_id"]

    # Fetch expenses for January 2026
    fetch = client.get("/expenses?year=2026&month=1")
    assert fetch.status_code == 200, fetch.text
    expenses = fetch.json()["expenses"]
    ids = {e["id"] for e in expenses}
    assert new_id in ids

    created = next(e for e in expenses if e["id"] == new_id)
    assert created["date"]["day"] == 1
    assert created["date"]["month"] == 1
    assert created["date"]["year"] == 2026


def test_create_expense_missing_required_fields():
    """POST /expenses with missing fields returns 422."""
    resp = client.post("/expenses", json={"amount": 10.0})
    assert resp.status_code == 422


def test_create_expense_invalid_date_format():
    """POST /expenses with a malformed date dict returns 400."""
    payload = {
        "expense_name": "Bad Date",
        "amount": 5.00,
        "category": "COFFEE",
        "date": {"bad_key": 99},
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 400


def test_create_expense_category_stored_as_provided():
    """Category string is stored exactly as given (uppercased)."""
    payload = {
        "expense_name": "Uber Ride",
        "amount": 12.50,
        "category": "ride_share",  # lowercase — endpoint should uppercase it
        "date": _today_dict(),
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["expense_id"]

    after = get_expenses_for_test_user()
    created = next((e for e in after if e["id"] == new_id), None)
    assert created is not None
    assert created["category"] == "RIDE_SHARE"


def test_create_expense_notes_round_trip():
    """Direct expense creation persists notes and returns them from GET routes."""
    payload = {
        "expense_name": "Annotated Expense",
        "amount": 18.25,
        "category": "OTHER",
        "date": _today_dict(),
        "notes": "split with Sam",
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    expense_id = resp.json()["expense_id"]

    detail = client.get(f"/expenses/{expense_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["expense"]["notes"] == "split with Sam"


def test_get_expenses_supports_date_range_queries():
    """GET /expenses can return a custom date range instead of only a month slice."""
    older_payload = {
        "expense_name": "Range Start",
        "amount": 11.00,
        "category": "COFFEE",
        "date": {"day": 2, "month": 1, "year": 2026},
    }
    newer_payload = {
        "expense_name": "Range End",
        "amount": 22.00,
        "category": "COFFEE",
        "date": {"day": 20, "month": 1, "year": 2026},
    }
    outside_payload = {
        "expense_name": "Outside Range",
        "amount": 33.00,
        "category": "COFFEE",
        "date": {"day": 5, "month": 2, "year": 2026},
    }

    for payload in (older_payload, newer_payload, outside_payload):
        resp = client.post("/expenses", json=payload)
        assert resp.status_code == 200, resp.text

    resp = client.get("/expenses?start_date=2026-01-01&end_date=2026-01-31")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    names = {expense["expense_name"] for expense in data["expenses"]}
    assert "Range Start" in names
    assert "Range End" in names
    assert "Outside Range" not in names
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] == "2026-01-31"


def test_update_expense_notes_persist():
    """PUT /expenses/{id} stores updated notes."""
    create = client.post("/expenses", json={
        "expense_name": "Update Notes",
        "amount": 7.50,
        "category": "COFFEE",
        "date": _today_dict(),
    })
    assert create.status_code == 200, create.text
    expense_id = create.json()["expense_id"]

    update = client.put(f"/expenses/{expense_id}", json={"notes": "oat milk"})
    assert update.status_code == 200, update.text

    detail = client.get(f"/expenses/{expense_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["expense"]["notes"] == "oat milk"


def test_unauthenticated_request_returns_401():
    """POST /expenses without an auth token returns 401."""
    # Temporarily remove the auth override to test real auth enforcement
    app.dependency_overrides.pop(get_current_user, None)
    try:
        unauthed_client = TestClient(app, raise_server_exceptions=False)
        resp = unauthed_client.post("/expenses", json={
            "expense_name": "Ghost Expense",
            "amount": 5.00,
            "category": "COFFEE",
            "date": _today_dict(),
        })
        assert resp.status_code == 401, resp.text
    finally:
        # Restore the override so subsequent tests are unaffected
        app.dependency_overrides[get_current_user] = override_auth


def test_multiple_expenses_same_day_get_unique_ids():
    """Two expenses on the same day each get a distinct Firestore document ID."""
    payload = {
        "expense_name": "Morning Coffee",
        "amount": 3.50,
        "category": "COFFEE",
        "date": _today_dict(),
    }
    id1 = client.post("/expenses", json=payload).json()["expense_id"]
    id2 = client.post("/expenses", json=payload).json()["expense_id"]
    assert id1 != id2, "Two separate expenses should have distinct IDs"


def test_amount_precision_preserved():
    """Decimal amounts are stored and retrieved without rounding."""
    payload = {
        "expense_name": "Precise Lunch",
        "amount": 14.37,
        "category": "FOOD_OUT",
        "date": _today_dict(),
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["expense_id"]

    expenses = get_expenses_for_test_user()
    created = next((e for e in expenses if e["id"] == new_id), None)
    assert created is not None
    assert abs(created["amount"] - 14.37) < 0.001


def test_expense_name_with_special_characters():
    """Expense names with unicode and special chars round-trip correctly."""
    name = "Café Zürich — espresso ☕"
    payload = {
        "expense_name": name,
        "amount": 6.00,
        "category": "COFFEE",
        "date": _today_dict(),
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["expense_id"]

    expenses = get_expenses_for_test_user()
    created = next((e for e in expenses if e["id"] == new_id), None)
    assert created is not None
    assert created["expense_name"] == name


def test_future_date_accepted():
    """Expenses with a future date are accepted and retrievable."""
    future_date = {"day": 28, "month": 12, "year": 2099}
    payload = {
        "expense_name": "Future Dinner",
        "amount": 100.00,
        "category": "FOOD_OUT",
        "date": future_date,
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["expense_id"]

    fetch = client.get("/expenses?year=2099&month=12")
    assert fetch.status_code == 200, fetch.text
    ids = {e["id"] for e in fetch.json()["expenses"]}
    assert new_id in ids


def test_user_isolation():
    """Expenses saved by one user are not visible to a different user."""
    # Save an expense as test user A
    payload = {
        "expense_name": "User A Secret",
        "amount": 99.99,
        "category": "OTHER",
        "date": _today_dict(),
    }
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 200, resp.text
    expense_id = resp.json()["expense_id"]

    # Switch the auth override to a different user
    other_uid = "test-user-other"
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        uid=other_uid, email="other@example.com", email_verified=True
    )
    try:
        now = datetime.now()
        other_resp = client.get(f"/expenses?year={now.year}&month={now.month}")
        assert other_resp.status_code == 200
        other_ids = {e["id"] for e in other_resp.json()["expenses"]}
        assert expense_id not in other_ids, "User B should not see User A's expense"
    finally:
        app.dependency_overrides[get_current_user] = override_auth
