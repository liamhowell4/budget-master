"""
Conversation Cache - In-memory storage for conversation state.

Handles:
- Tracking recent expenses per user (phone number or session ID)
- Enabling multi-turn conversations ("actually that was $6")
- Auto-cleanup of stale entries

Architecture:
- In-memory Python dict (no Firestore overhead)
- Single-user optimized
- Lost on restart (acceptable for short-term context)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz

logger = logging.getLogger(__name__)


class ConversationCache:
    """
    In-memory cache for conversation state.

    Tracks recent expenses per user to enable context-aware edits:
    - "Actually that was $6" → Updates last expense
    - "Delete that" → Removes last expense
    - "Delete the second one" → Removes from recent list
    """

    def __init__(self):
        """Initialize empty conversation cache."""
        self._cache: Dict[str, Dict[str, Any]] = {}

    def update_last_expense(self, user_id: str, expense_id: str, expense_name: str, amount: float, category: str):
        """
        Track the most recent expense for a user.

        Args:
            user_id: Phone number or session ID
            expense_id: Firebase document ID
            expense_name: Human-readable expense name
            amount: Dollar amount
            category: Expense category (e.g., "COFFEE")
        """
        now = self._get_current_time()

        if user_id not in self._cache:
            self._cache[user_id] = {
                "last_expense_id": None,
                "recent_expenses": [],
                "last_updated": None
            }

        # Add to recent expenses list (maintain last 5)
        expense_data = {
            "expense_id": expense_id,
            "expense_name": expense_name,
            "amount": amount,
            "category": category,
            "timestamp": now
        }

        recent = self._cache[user_id]["recent_expenses"]
        recent.insert(0, expense_data)  # Add to front
        self._cache[user_id]["recent_expenses"] = recent[:5]  # Keep last 5

        # Update last expense ID
        self._cache[user_id]["last_expense_id"] = expense_id
        self._cache[user_id]["last_updated"] = now

    def get_last_expense_id(self, user_id: str) -> Optional[str]:
        """
        Get the most recent expense ID for a user.

        Args:
            user_id: Phone number or session ID

        Returns:
            Expense ID or None if no recent expenses
        """
        if user_id not in self._cache:
            return None

        return self._cache[user_id].get("last_expense_id")

    def get_recent_expenses(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent expenses for a user.

        Args:
            user_id: Phone number or session ID
            limit: Maximum number of expenses to return (default 5)

        Returns:
            List of expense dicts with: expense_id, expense_name, amount, category, timestamp
        """
        if user_id not in self._cache:
            return []

        recent = self._cache[user_id].get("recent_expenses", [])
        return recent[:limit]

    def cleanup_old(self, ttl_hours: int = 24):
        """
        Remove stale cache entries older than TTL.

        Args:
            ttl_hours: Time-to-live in hours (default 24)
        """
        now = self._get_current_time()
        cutoff = now - timedelta(hours=ttl_hours)

        # Find stale user IDs
        stale_users = [
            user_id
            for user_id, data in self._cache.items()
            if data.get("last_updated") and data["last_updated"] < cutoff
        ]

        # Remove stale entries
        for user_id in stale_users:
            del self._cache[user_id]

        if stale_users:
            logger.info("Cleaned up %d stale conversation cache entries", len(stale_users))

    def get_cache_size(self) -> int:
        """
        Get the number of users in the cache.

        Returns:
            Number of cached users
        """
        return len(self._cache)

    def clear_user(self, user_id: str):
        """
        Clear conversation state for a specific user.

        Args:
            user_id: Phone number or session ID
        """
        if user_id in self._cache:
            del self._cache[user_id]

    def clear_all(self):
        """Clear all conversation state (useful for testing)."""
        self._cache.clear()

    def _get_current_time(self) -> datetime:
        """
        Get current time in user's timezone.

        Returns:
            Timezone-aware datetime
        """
        user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
        tz = pytz.timezone(user_timezone)
        return datetime.now(tz)


# Global cache instance (singleton pattern for FastAPI)
_conversation_cache: Optional[ConversationCache] = None


def get_conversation_cache() -> ConversationCache:
    """
    Get the global conversation cache instance.

    Returns:
        Singleton ConversationCache instance
    """
    global _conversation_cache
    if _conversation_cache is None:
        _conversation_cache = ConversationCache()
    return _conversation_cache
