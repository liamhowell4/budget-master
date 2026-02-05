from pydantic import BaseModel, field_validator
from enum import Enum
from typing import Optional
from datetime import datetime
import re

class ExpenseType(Enum):
    FOOD_OUT = "dinner/lunch/breakfast/snacks, etc at a restaurant. Does NOT include coffee shops or buying coffee"
    RENT = "apartment rent"
    UTILITIES = "utilities (electricity, water, internet, etc.)"
    MEDICAL = "medical (doctor, dentist, etc.) and prescription costs"
    GAS = "gas (gasoline, diesel, etc. for the car)"
    GROCERIES = "groceries (food, household items, etc.)"
    RIDE_SHARE = "taxi/lyft/uber"
    COFFEE = "coffee shops, eating coffee, etc."
    HOTEL = "hotel"
    TECH = "technology (ie software subscription, ai subscriptions, etc.)"
    TRAVEL = "airfare (airline tickets)/Hotel/Travel Agency/rental car etc."
    OTHER = "other"

class FrequencyType(Enum):
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"

class Date(BaseModel):
    day: int
    month: int
    year: int

class Expense(BaseModel):
    expense_name: str
    amount: float
    date: Date
    category: ExpenseType

class RecurringExpense(BaseModel):
    """Template for recurring expenses (rent, subscriptions, etc.)"""
    template_id: Optional[str] = None
    expense_name: str
    amount: float
    category: ExpenseType
    frequency: FrequencyType
    day_of_month: Optional[int] = None  # 1-31 for monthly
    day_of_week: Optional[int] = None  # 0-6 for weekly/biweekly (0=Monday)
    last_of_month: bool = False  # True if user specified "last day of month"
    last_reminded: Optional[Date] = None  # When we last created pending expense
    last_user_action: Optional[Date] = None  # When user last confirmed/skipped/edited
    active: bool = True  # False if user canceled

class PendingExpense(BaseModel):
    """Pending expense awaiting user confirmation"""
    pending_id: Optional[str] = None
    template_id: str  # Reference to recurring_expense
    expense_name: str
    amount: float
    date: Date  # When expense is due
    category: ExpenseType
    sms_sent: bool = False  # Whether SMS confirmation was sent
    awaiting_confirmation: bool = True  # False once user responds

class RecurringDetectionResult(BaseModel):
    """Result of AI detecting whether text describes a recurring expense"""
    is_recurring: bool
    confidence: float  # 0-1 confidence score
    recurring_expense: Optional[RecurringExpense] = None
    explanation: str  # Why AI thinks it's recurring or not


# ==================== Custom Categories Models ====================

def generate_category_id(display_name: str) -> str:
    """
    Generate a category ID from a display name.

    Converts "Food & Dining" to "FOOD_DINING"

    Args:
        display_name: User-facing category name

    Returns:
        UPPER_SNAKE_CASE category ID
    """
    # Remove special characters except spaces
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', display_name)
    # Replace spaces with underscores and uppercase
    return '_'.join(cleaned.upper().split())


class Category(BaseModel):
    """User-defined expense category with budget cap."""
    category_id: str  # UPPER_SNAKE_CASE identifier
    display_name: str  # User-facing name (e.g., "Food & Dining")
    icon: str  # Lucide icon name (e.g., "utensils")
    color: str  # Hex color (e.g., "#EF4444")
    monthly_cap: float  # Budget cap for this category
    is_system: bool = False  # True for OTHER (cannot be deleted)
    created_at: Optional[datetime] = None
    sort_order: int = 0
    exclude_from_total: bool = False  # If True, this category won't count toward overall budget total


class CategoryCreate(BaseModel):
    """Request model for creating a new category."""
    display_name: str  # 1-30 characters
    icon: str
    color: str
    monthly_cap: float  # Must be <= available budget

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1 or len(v) > 30:
            raise ValueError('display_name must be 1-30 characters')
        if not re.match(r'^[a-zA-Z0-9\s&/\-]+$', v):
            raise ValueError('display_name can only contain letters, numbers, spaces, &, /, and -')
        return v

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('color must be a valid hex color (e.g., #EF4444)')
        return v

    @field_validator('monthly_cap')
    @classmethod
    def validate_monthly_cap(cls, v: float) -> float:
        if v < 0:
            raise ValueError('monthly_cap must be non-negative')
        return v


class CategoryUpdate(BaseModel):
    """Request model for updating a category."""
    display_name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    monthly_cap: Optional[float] = None
    sort_order: Optional[int] = None
    exclude_from_total: Optional[bool] = None  # If True, exclude from overall budget total

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 1 or len(v) > 30:
            raise ValueError('display_name must be 1-30 characters')
        if not re.match(r'^[a-zA-Z0-9\s&/\-]+$', v):
            raise ValueError('display_name can only contain letters, numbers, spaces, &, /, and -')
        return v

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('color must be a valid hex color (e.g., #EF4444)')
        return v

    @field_validator('monthly_cap')
    @classmethod
    def validate_monthly_cap(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError('monthly_cap must be non-negative')
        return v


class CategoryReorder(BaseModel):
    """Request model for reordering categories."""
    category_ids: list[str]  # List of category IDs in desired order
