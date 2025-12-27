from pydantic import BaseModel
from enum import Enum

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

class Date(BaseModel):
    day: int
    month: int
    year: int

class Expense(BaseModel):
    expense_name: str
    amount: float
    date: Date
    category: ExpenseType
