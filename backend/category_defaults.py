"""
Category Defaults - Default category configuration for new users.

Contains the default categories that new users start with, along with
their icons, colors, and descriptions.
"""

from typing import Dict, Any, List


# Default categories with their configuration
# Used when migrating from old budget_caps or initializing new users
DEFAULT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "FOOD_OUT": {
        "display_name": "Food & Dining",
        "icon": "utensils",
        "color": "#EF4444",
        "description": "dinner/lunch/breakfast/snacks at restaurants"
    },
    "GROCERIES": {
        "display_name": "Groceries",
        "icon": "shopping-cart",
        "color": "#84CC16",
        "description": "groceries, food, household items"
    },
    "RENT": {
        "display_name": "Rent/Mortgage",
        "icon": "home",
        "color": "#3B82F6",
        "description": "apartment rent or mortgage payments"
    },
    "UTILITIES": {
        "display_name": "Utilities",
        "icon": "zap",
        "color": "#F97316",
        "description": "electricity, water, internet, etc."
    },
    "GAS": {
        "display_name": "Gas/Fuel",
        "icon": "fuel",
        "color": "#F59E0B",
        "description": "gasoline, diesel for car"
    },
    "TRANSPORTATION": {
        "display_name": "Transportation",
        "icon": "car",
        "color": "#6366F1",
        "description": "general transportation expenses"
    },
    "MEDICAL": {
        "display_name": "Medical/Health",
        "icon": "heart-pulse",
        "color": "#14B8A6",
        "description": "doctor, dentist, prescriptions"
    },
    "COFFEE": {
        "display_name": "Coffee",
        "icon": "coffee",
        "color": "#92400E",
        "description": "coffee shops, coffee purchases"
    },
    "TECH": {
        "display_name": "Tech/Electronics",
        "icon": "laptop",
        "color": "#06B6D4",
        "description": "software subscriptions, electronics"
    },
    "TRAVEL": {
        "display_name": "Travel",
        "icon": "plane",
        "color": "#8B5CF6",
        "description": "airfare, travel expenses"
    },
    "HOTEL": {
        "display_name": "Hotels",
        "icon": "bed",
        "color": "#EC4899",
        "description": "hotel stays"
    },
    "RIDE_SHARE": {
        "display_name": "Ride Share",
        "icon": "car-taxi-front",
        "color": "#6366F1",
        "description": "taxi, Lyft, Uber"
    },
    "OTHER": {
        "display_name": "Other",
        "icon": "more-horizontal",
        "color": "#6B7280",
        "description": "miscellaneous expenses",
        "is_system": True  # Cannot be deleted
    },
}

# Categories that are pre-selected by default for new users
# These are the most commonly used categories
COMMON_PRESELECTED: List[str] = [
    "FOOD_OUT",
    "GROCERIES",
    "RENT",
    "UTILITIES",
    "TRANSPORTATION",
    "OTHER"
]

# Maximum number of categories a user can have
MAX_CATEGORIES = 20


def get_default_category(category_id: str) -> Dict[str, Any]:
    """
    Get default configuration for a category.

    Args:
        category_id: The category ID (e.g., "FOOD_OUT")

    Returns:
        Category configuration dict or empty dict if not found
    """
    return DEFAULT_CATEGORIES.get(category_id, {})


def get_all_default_category_ids() -> List[str]:
    """
    Get all default category IDs.

    Returns:
        List of category IDs
    """
    return list(DEFAULT_CATEGORIES.keys())
