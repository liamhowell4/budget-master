"""
Intent-based MCP tool filtering.

Classifies user messages by intent and returns only the relevant tool subset,
reducing token usage on tool definitions sent to Claude.
"""

import re
from enum import Enum, auto


class Intent(Enum):
    SAVE = auto()
    QUERY = auto()
    EDIT = auto()
    RECURRING = auto()
    BUDGET = auto()


INTENT_TOOLS: dict[Intent, set[str]] = {
    Intent.SAVE: {"save_expense", "get_budget_status", "get_categories", "get_recent_expenses"},
    Intent.QUERY: {
        "query_expenses", "get_spending_by_category", "get_spending_summary",
        "get_budget_remaining", "compare_periods", "get_largest_expenses",
    },
    Intent.EDIT: {"update_expense", "delete_expense", "get_recent_expenses", "search_expenses"},
    Intent.RECURRING: {
        "create_recurring_expense", "list_recurring_expenses",
        "delete_recurring_expense", "get_categories",
    },
    Intent.BUDGET: {"get_budget_remaining", "get_budget_status"},
}

ALWAYS_INCLUDE = {"get_categories"}

# Compiled patterns per intent
_INTENT_PATTERNS: dict[Intent, list[re.Pattern]] = {
    Intent.SAVE: [
        re.compile(r"\$\d+", re.IGNORECASE),
        re.compile(r"\d+\s*dollars", re.IGNORECASE),
        re.compile(r"\b(?:add|log|spent|paid|bought|grabbed|picked up|cost)\b", re.IGNORECASE),
    ],
    Intent.QUERY: [
        re.compile(r"\bhow much\b", re.IGNORECASE),
        re.compile(r"\b(?:spending|spend)\b", re.IGNORECASE),
        re.compile(r"\b(?:total|breakdown|summary)\b", re.IGNORECASE),
        re.compile(r"\b(?:compare|vs)\b", re.IGNORECASE),
        re.compile(r"\b(?:biggest|largest)\s+expense", re.IGNORECASE),
        re.compile(r"\bshow\b.*\bexpenses?\b", re.IGNORECASE),
        re.compile(r"\b(?:last week|this month|this week|last month|today|yesterday)\b", re.IGNORECASE),
    ],
    Intent.EDIT: [
        re.compile(r"\b(?:change|update|edit|delete|remove|undo)\b", re.IGNORECASE),
        re.compile(r"\b(?:actually|that was|should be|meant to say)\b", re.IGNORECASE),
    ],
    Intent.RECURRING: [
        re.compile(r"\b(?:recurring|subscription|subscriptions)\b", re.IGNORECASE),
        re.compile(r"\b(?:every\s+(?:month|week|day)|monthly|weekly|biweekly)\b", re.IGNORECASE),
        re.compile(r"\bset up\b.*\bexpense\b", re.IGNORECASE),
        re.compile(r"\bcancel\b.*\bsubscription\b", re.IGNORECASE),
    ],
    Intent.BUDGET: [
        re.compile(r"\bbudget\b", re.IGNORECASE),
        re.compile(r"\b(?:remaining|left)\b", re.IGNORECASE),
        re.compile(r"\b(?:over|under)\s+budget\b", re.IGNORECASE),
    ],
}


def classify_intent(message: str) -> set[Intent]:
    """Classify user message into a set of intents based on keyword/regex matching.

    Returns an empty set if no intent is matched (safe fallback — all tools used).
    """
    intents: set[Intent] = set()
    for intent, patterns in _INTENT_PATTERNS.items():
        if any(p.search(message) for p in patterns):
            intents.add(intent)
    return intents


def filter_tools(all_tools: list[dict], intents: set[Intent]) -> list[dict]:
    """Filter tool list to only include tools relevant to the matched intents.

    If intents is empty, returns all tools unchanged (safe fallback).
    """
    if not intents:
        return all_tools

    allowed_names = set(ALWAYS_INCLUDE)
    for intent in intents:
        allowed_names |= INTENT_TOOLS[intent]

    return [t for t in all_tools if t["name"] in allowed_names]
