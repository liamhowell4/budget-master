"""
Tests for custom category support in the MCP expense server.

Covers:
- validate_category: exact match, case-insensitive, display name, invalid
- _get_categories: returns custom categories when auth works
- _save_expense: accepts custom category, rejects invalid
- _update_expense: accepts custom category
- chat_helpers: auth_token is injected for get_categories
"""

import asyncio
import sys
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.mcp.expense_server import validate_category, _get_categories, _save_expense, _update_expense
from backend.exceptions import InvalidCategoryError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CUSTOM_CATS = [
    {"category_id": "FOOD_OUT", "display_name": "Food & Dining", "sort_order": 0},
    {"category_id": "THERAPY", "display_name": "Therapy", "sort_order": 1},
    {"category_id": "PET_SUPPLIES", "display_name": "Pet Supplies", "sort_order": 2},
]


def make_firebase(has_categories=True, categories=None):
    """Return a mock FirebaseClient with custom categories configured."""
    fb = MagicMock()
    fb.user_id = "test_user_123"
    fb.has_categories_setup.return_value = has_categories
    fb.get_user_categories.return_value = categories if categories is not None else CUSTOM_CATS
    fb.save_expense.return_value = "expense_abc123"
    fb.get_expense_by_id.return_value = {
        "expense_name": "Test",
        "amount": 50.0,
        "category": "THERAPY",
    }
    return fb


def make_budget_manager():
    bm = MagicMock()
    bm.get_budget_status_data.return_value = {
        "warning": "",
        "category_remaining": None,
        "total_remaining": None,
    }
    return bm


# ---------------------------------------------------------------------------
# validate_category tests
# ---------------------------------------------------------------------------

def test_validate_exact_match():
    fb = make_firebase()
    result = validate_category("THERAPY", fb)
    assert result == "THERAPY"


def test_validate_case_insensitive():
    """Model may send 'therapy' or 'THERAPY' — both should resolve."""
    fb = make_firebase()
    assert validate_category("therapy", fb) == "THERAPY"
    assert validate_category("THERAPY", fb) == "THERAPY"
    assert validate_category("Therapy", fb) == "THERAPY"  # mixed case


def test_validate_display_name():
    """Model may send the friendly display name instead of the key."""
    fb = make_firebase()
    assert validate_category("Therapy", fb) == "THERAPY"
    assert validate_category("Food & Dining", fb) == "FOOD_OUT"
    assert validate_category("Pet Supplies", fb) == "PET_SUPPLIES"


def test_validate_invalid_category_raises():
    fb = make_firebase()
    try:
        validate_category("NONEXISTENT", fb)
        assert False, "Should have raised InvalidCategoryError"
    except InvalidCategoryError:
        pass


def test_validate_fallback_to_enum_when_no_custom_categories():
    """When user has no custom categories, falls back to ExpenseType enum."""
    fb = make_firebase(has_categories=False)
    result = validate_category("FOOD_OUT", fb)
    assert result == "FOOD_OUT"


def test_validate_fallback_enum_case_insensitive():
    fb = make_firebase(has_categories=False)
    result = validate_category("food_out", fb)
    assert result == "FOOD_OUT"


def test_validate_fallback_enum_invalid():
    fb = make_firebase(has_categories=False)
    try:
        validate_category("THERAPY", fb)
        assert False, "Should raise — THERAPY not in ExpenseType"
    except InvalidCategoryError:
        pass


# ---------------------------------------------------------------------------
# _get_categories tests
# ---------------------------------------------------------------------------

def test_get_categories_returns_custom():
    """_get_categories should return custom categories when auth works."""
    with patch("backend.mcp.expense_server.get_user_firebase") as mock_guf:
        mock_guf.return_value = make_firebase()
        result = asyncio.run(_get_categories({"auth_token": "tok"}))

    assert len(result) == 1
    data = json.loads(result[0].text)
    keys = [c["key"] for c in data["categories"]]
    assert "THERAPY" in keys
    assert "PET_SUPPLIES" in keys
    assert "FOOD_OUT" in keys


def test_get_categories_fallback_when_no_custom():
    """Falls back to ExpenseType list when user has no custom categories."""
    fb = make_firebase(has_categories=False, categories=[])
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb):
        result = asyncio.run(_get_categories({"auth_token": "tok"}))

    data = json.loads(result[0].text)
    keys = [c["key"] for c in data["categories"]]
    assert "FOOD_OUT" in keys
    assert "COFFEE" in keys


def test_get_categories_requires_auth_token():
    """Calling without auth_token propagates the ValueError to the MCP error handler."""
    with patch("backend.mcp.expense_server.get_user_firebase", side_effect=ValueError("auth_token is required")):
        try:
            asyncio.run(_get_categories({}))
            assert False, "Should have raised"
        except ValueError as e:
            assert "auth_token" in str(e)


# ---------------------------------------------------------------------------
# _save_expense tests
# ---------------------------------------------------------------------------

def make_save_args(category="THERAPY"):
    return {
        "auth_token": "tok",
        "name": "Therapy session",
        "amount": 150.0,
        "date": {"day": 1, "month": 3, "year": 2026},
        "category": category,
    }


def test_save_expense_with_custom_category():
    fb = make_firebase()
    bm = make_budget_manager()
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb), \
         patch("backend.mcp.expense_server.get_user_budget_manager", return_value=bm):
        result = asyncio.run(_save_expense(make_save_args("THERAPY")))

    data = json.loads(result[0].text)
    assert data["success"] is True
    assert data["expense_id"] == "expense_abc123"
    assert data["category"] == "THERAPY"


def test_save_expense_with_display_name():
    """Model passes display name 'Therapy' — should resolve and save correctly."""
    fb = make_firebase()
    bm = make_budget_manager()
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb), \
         patch("backend.mcp.expense_server.get_user_budget_manager", return_value=bm):
        result = asyncio.run(_save_expense(make_save_args("Therapy")))

    data = json.loads(result[0].text)
    assert data["success"] is True
    assert data["category"] == "THERAPY"  # canonical ID, not display name


def test_save_expense_with_lowercase_key():
    """Model passes lowercase key 'therapy' — should resolve."""
    fb = make_firebase()
    bm = make_budget_manager()
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb), \
         patch("backend.mcp.expense_server.get_user_budget_manager", return_value=bm):
        result = asyncio.run(_save_expense(make_save_args("therapy")))

    data = json.loads(result[0].text)
    assert data["success"] is True
    assert data["category"] == "THERAPY"


def test_save_expense_rejects_invalid_category():
    fb = make_firebase()
    bm = make_budget_manager()
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb), \
         patch("backend.mcp.expense_server.get_user_budget_manager", return_value=bm):
        result = asyncio.run(_save_expense(make_save_args("TOTALLY_FAKE")))

    text = result[0].text
    assert "Invalid category" in text or "error" in text.lower()


def test_save_expense_default_category_still_works():
    """Default categories like FOOD_OUT must continue to work."""
    fb = make_firebase()
    bm = make_budget_manager()
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb), \
         patch("backend.mcp.expense_server.get_user_budget_manager", return_value=bm):
        result = asyncio.run(_save_expense(make_save_args("FOOD_OUT")))

    data = json.loads(result[0].text)
    assert data["success"] is True
    assert data["category"] == "FOOD_OUT"


# ---------------------------------------------------------------------------
# _update_expense tests
# ---------------------------------------------------------------------------

def make_update_args(category="THERAPY"):
    return {
        "auth_token": "tok",
        "expense_id": "expense_abc123",
        "category": category,
    }


def test_update_expense_with_custom_category():
    fb = make_firebase()
    fb.update_expense.return_value = None
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb):
        result = asyncio.run(_update_expense(make_update_args("THERAPY")))

    data = json.loads(result[0].text)
    assert data["success"] is True


def test_update_expense_rejects_invalid_category():
    fb = make_firebase()
    with patch("backend.mcp.expense_server.get_user_firebase", return_value=fb):
        result = asyncio.run(_update_expense(make_update_args("BOGUS_CAT")))

    text = result[0].text
    assert "Invalid category" in text or "error" in text.lower()


# ---------------------------------------------------------------------------
# chat_helpers: auth_token injection for get_categories
# ---------------------------------------------------------------------------

def test_chat_helpers_injects_auth_for_get_categories():
    """
    After the fix, auth_token must be injected for get_categories just like
    every other tool. Verify the special-case exclusion is gone.
    """
    import inspect
    import backend.chat_helpers as ch

    source = inspect.getsource(ch._run_anthropic_streaming_loop)
    assert 'if tool_name != "get_categories"' not in source, (
        "auth_token injection should not exclude get_categories"
    )

    source2 = inspect.getsource(ch._run_non_anthropic_tool_loop)
    assert 'if tool_name != "get_categories"' not in source2, (
        "auth_token injection should not exclude get_categories (non-anthropic path)"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
