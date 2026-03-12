"""Tests for intent_classifier module."""

import pytest
from backend.intent_classifier import Intent, classify_intent, filter_tools, ALWAYS_INCLUDE, INTENT_TOOLS


# ── classify_intent tests ──


class TestClassifyIntentSave:
    def test_dollar_amount(self):
        assert Intent.SAVE in classify_intent("coffee $5")

    def test_dollars_word(self):
        assert Intent.SAVE in classify_intent("lunch was 15 dollars")

    def test_spent_keyword(self):
        assert Intent.SAVE in classify_intent("I spent money on groceries")

    def test_bought_keyword(self):
        assert Intent.SAVE in classify_intent("bought a new shirt")

    def test_paid_keyword(self):
        assert Intent.SAVE in classify_intent("paid the electric bill")


class TestClassifyIntentQuery:
    def test_how_much(self):
        assert Intent.QUERY in classify_intent("how much did I spend on food?")

    def test_spending(self):
        assert Intent.QUERY in classify_intent("what's my spending this month?")

    def test_total(self):
        assert Intent.QUERY in classify_intent("total for groceries")

    def test_breakdown(self):
        assert Intent.QUERY in classify_intent("give me a breakdown by category")

    def test_summary(self):
        assert Intent.QUERY in classify_intent("spending summary")

    def test_compare(self):
        assert Intent.QUERY in classify_intent("compare this month vs last month")

    def test_largest(self):
        assert Intent.QUERY in classify_intent("what was my biggest expense?")

    def test_show_expenses(self):
        assert Intent.QUERY in classify_intent("show me my expenses")

    def test_time_phrase(self):
        assert Intent.QUERY in classify_intent("what about last week?")


class TestClassifyIntentEdit:
    def test_delete(self):
        assert Intent.EDIT in classify_intent("delete that last expense")

    def test_remove(self):
        assert Intent.EDIT in classify_intent("remove the coffee entry")

    def test_change(self):
        assert Intent.EDIT in classify_intent("change the amount to $10")

    def test_update(self):
        assert Intent.EDIT in classify_intent("update the category")

    def test_correction_actually(self):
        assert Intent.EDIT in classify_intent("actually that was $6")

    def test_correction_should_be(self):
        assert Intent.EDIT in classify_intent("the amount should be 12")


class TestClassifyIntentRecurring:
    def test_recurring(self):
        assert Intent.RECURRING in classify_intent("set up a recurring expense for rent")

    def test_subscription(self):
        assert Intent.RECURRING in classify_intent("my subscriptions")

    def test_monthly(self):
        assert Intent.RECURRING in classify_intent("I pay this monthly")

    def test_every_month(self):
        assert Intent.RECURRING in classify_intent("it happens every month")

    def test_cancel_subscription(self):
        assert Intent.RECURRING in classify_intent("cancel my Netflix subscription")


class TestClassifyIntentBudget:
    def test_budget(self):
        assert Intent.BUDGET in classify_intent("what's my budget?")

    def test_remaining(self):
        assert Intent.BUDGET in classify_intent("how much remaining?")

    def test_left(self):
        assert Intent.BUDGET in classify_intent("how much do I have left?")

    def test_over_budget(self):
        assert Intent.BUDGET in classify_intent("am I over budget?")


class TestClassifyIntentMulti:
    def test_edit_and_save(self):
        result = classify_intent("delete that coffee and add a new one for $6")
        assert Intent.EDIT in result
        assert Intent.SAVE in result

    def test_query_and_budget(self):
        result = classify_intent("how much budget remaining this month?")
        assert Intent.BUDGET in result
        # "this month" or "how much" may also trigger QUERY
        assert Intent.QUERY in result


class TestClassifyIntentFallback:
    def test_empty_string(self):
        assert classify_intent("") == set()

    def test_greeting(self):
        assert classify_intent("hello") == set()

    def test_thanks(self):
        assert classify_intent("thanks!") == set()

    def test_random_question(self):
        assert classify_intent("what time is it?") == set()


# ── filter_tools tests ──


def _make_tools(names: list[str]) -> list[dict]:
    """Create minimal tool dicts for testing."""
    return [{"name": n, "description": f"Tool {n}", "input_schema": {}} for n in names]


ALL_TOOL_NAMES = sorted(
    {name for tools in INTENT_TOOLS.values() for name in tools} | ALWAYS_INCLUDE
)


class TestFilterTools:
    def test_empty_intents_returns_all(self):
        tools = _make_tools(["save_expense", "query_expenses", "get_categories"])
        result = filter_tools(tools, set())
        assert result == tools

    def test_single_intent_filters(self):
        tools = _make_tools(ALL_TOOL_NAMES)
        result = filter_tools(tools, {Intent.SAVE})
        result_names = {t["name"] for t in result}
        expected = INTENT_TOOLS[Intent.SAVE] | ALWAYS_INCLUDE
        assert result_names == expected

    def test_multi_intent_unions(self):
        tools = _make_tools(ALL_TOOL_NAMES)
        result = filter_tools(tools, {Intent.SAVE, Intent.EDIT})
        result_names = {t["name"] for t in result}
        expected = INTENT_TOOLS[Intent.SAVE] | INTENT_TOOLS[Intent.EDIT] | ALWAYS_INCLUDE
        assert result_names == expected

    def test_get_categories_always_included(self):
        tools = _make_tools(ALL_TOOL_NAMES)
        for intent in Intent:
            result = filter_tools(tools, {intent})
            result_names = {t["name"] for t in result}
            assert "get_categories" in result_names

    def test_preserves_tool_structure(self):
        tools = [{"name": "save_expense", "description": "Save", "input_schema": {"type": "object"}}]
        result = filter_tools(tools, {Intent.SAVE})
        assert result[0]["description"] == "Save"
        assert result[0]["input_schema"] == {"type": "object"}

    def test_unknown_tool_names_excluded(self):
        tools = _make_tools(["save_expense", "unknown_tool"])
        result = filter_tools(tools, {Intent.SAVE})
        result_names = {t["name"] for t in result}
        assert "unknown_tool" not in result_names
