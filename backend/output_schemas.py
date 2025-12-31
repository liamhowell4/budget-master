from pydantic import BaseModel
from enum import Enum
from typing import Optional

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
