"""
Expense Parser - Parse expenses from text, images, or voice transcriptions.

Supports:
- Text-only parsing (SMS, voice transcription)
- Image-only parsing (receipt photos)
- Combined text + image parsing
- Natural language date processing
"""

import base64
import json
from datetime import date, datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
import os

from .endpoints import Endpoints
from .output_schemas import Expense, ExpenseType, Date

load_dotenv(override=True)

def _parse_natural_language_date(date_str: str) -> Date:
    """
    Parse natural language dates like "yesterday", "last Tuesday", etc.

    Args:
        date_str: Natural language date string

    Returns:
        Date object
    """
    today = date.today()
    date_str_lower = date_str.lower().strip()

    # Handle "today"
    if date_str_lower in ["today", "now"]:
        return Date(day=today.day, month=today.month, year=today.year)

    # Handle "yesterday"
    if date_str_lower == "yesterday":
        yesterday = today - timedelta(days=1)
        return Date(day=yesterday.day, month=yesterday.month, year=yesterday.year)

    # Handle "last [day of week]" - e.g., "last Tuesday"
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, weekday in enumerate(weekdays):
        if weekday in date_str_lower:
            # Calculate days back to that weekday
            days_back = (today.weekday() - i) % 7
            if days_back == 0:
                days_back = 7  # If it's today, assume they mean last week
            target_date = today - timedelta(days=days_back)
            return Date(day=target_date.day, month=target_date.month, year=target_date.year)

    # If we can't parse it, return today
    return Date(day=today.day, month=today.month, year=today.year)


def parse_text(text: str, context: Optional[str] = None) -> Expense:
    """
    Parse a text description of an expense.

    Args:
        text: Text description (e.g., "Coffee $5", "Chipotle lunch $15")
        context: Optional additional context

    Returns:
        Expense object
    """
    endpoints = Endpoints()
    client = endpoints.openai_client

    today = date.today()

    # Build the prompt for personal expenses
    prompt = f"""Parse this personal expense from the text description.

Text: {text}
{f"Additional context: {context}" if context else ""}

Extract the following information and return as JSON:

1. **expense_name**: A brief descriptive name for this expense (e.g., "Chipotle lunch", "Starbucks coffee", "Uber to airport"). Generate a clear name based on the description.

2. **amount**: The dollar amount as a number. If no amount is mentioned, use 0.

3. **date**: The date of the expense with day, month, and year as integers.
   - Parse natural language like "yesterday", "last Tuesday", etc.
   - If no date is mentioned, use today's date: day={today.day}, month={today.month}, year={today.year}
   - Return the actual calendar date (not the natural language string)

4. **category**: One of these exact category keys based on what the expense is for:
   - "FOOD_OUT" - dining out at restaurants (breakfast/lunch/dinner/snacks). Does NOT include coffee shops.
   - "RENT" - apartment rent
   - "UTILITIES" - utilities (electricity, water, internet, etc.)
   - "MEDICAL" - medical (doctor, dentist) and prescription costs
   - "GAS" - gasoline/diesel for car
   - "GROCERIES" - grocery shopping (food, household items)
   - "RIDE_SHARE" - taxi/Uber/Lyft rides
   - "COFFEE" - coffee shops and buying coffee
   - "HOTEL" - hotel accommodations
   - "TECH" - technology (software subscriptions, AI tools, etc.)
   - "TRAVEL" - airfare/airline tickets/rental car/travel agency fees
   - "OTHER" - anything else or if unclear

Return ONLY valid JSON in this exact format:
{{
    "expense_name": "string",
    "amount": number,
    "date": {{"day": number, "month": number, "year": number}},
    "category": "CATEGORY_KEY"
}}

IMPORTANT: Return the category KEY (like "FOOD_OUT"), not the description."""

    # Call GPT-4 for text parsing
    response = client.chat.completions.create(
        model=os.getenv("PROCESSING_MODEL"),
        messages=[{
            "role": "user",
            "content": prompt
        }],
        response_format={"type": "json_object"}
    )

    # Parse the response
    response_text = response.choices[0].message.content
    data = json.loads(response_text)

    # Map category string to ExpenseType enum
    category_str = data.get("category", "OTHER")
    try:
        category = ExpenseType[category_str]
    except KeyError:
        category = ExpenseType.OTHER

    # Parse date
    date_data = data.get("date", {})
    expense_date = Date(
        day=date_data.get("day", today.day),
        month=date_data.get("month", today.month),
        year=date_data.get("year", today.year)
    )

    # Build and return the Expense object
    expense = Expense(
        expense_name=data.get("expense_name", "Unknown expense"),
        amount=data.get("amount", 0),
        date=expense_date,
        category=category
    )

    return expense


def parse_image(image_bytes: bytes, context: Optional[str] = None) -> Expense:
    """
    Parse a receipt image to extract expense data.

    Args:
        image_bytes: Raw bytes of the receipt image
        context: Optional context string with additional info

    Returns:
        Expense object
    """
    endpoints = Endpoints()
    client = endpoints.openai_client

    # Encode image as base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    today = date.today()

    # Build the prompt for personal expenses
    prompt = f"""Analyze this receipt image and extract personal expense information.

{f"Additional context: {context}" if context else ""}

Extract the following information and return as JSON:

1. **expense_name**: A brief descriptive name for this expense based on the merchant/vendor name (e.g., "Whole Foods groceries", "Shell gas station", "Walgreens pharmacy").

2. **amount**: The total amount from the receipt as a number. Look for "Total", "Amount Due", or similar. If unclear, use 0.

3. **date**: The date of the expense with day, month, and year as integers.
   - If the date is visible on the receipt, use that.
   - If no date is found, use today's date: day={today.day}, month={today.month}, year={today.year}

4. **category**: One of these exact category keys based on what the expense is for:
   - "FOOD_OUT" - dining out at restaurants (breakfast/lunch/dinner/snacks). Does NOT include coffee shops.
   - "RENT" - apartment rent
   - "UTILITIES" - utilities (electricity, water, internet, etc.)
   - "MEDICAL" - medical (doctor, dentist) and prescription costs
   - "GAS" - gasoline/diesel for car
   - "GROCERIES" - grocery shopping (food, household items)
   - "RIDE_SHARE" - taxi/Uber/Lyft rides
   - "COFFEE" - coffee shops and buying coffee
   - "HOTEL" - hotel accommodations
   - "TECH" - technology (software subscriptions, AI tools, etc.)
   - "TRAVEL" - airfare/airline tickets/rental car/travel agency fees
   - "OTHER" - anything else or if unclear

Return ONLY valid JSON in this exact format:
{{
    "expense_name": "string",
    "amount": number,
    "date": {{"day": number, "month": number, "year": number}},
    "category": "CATEGORY_KEY"
}}

IMPORTANT: Return the category KEY (like "GROCERIES"), not the description."""

    # Call GPT-4 Vision
    response = client.chat.completions.create(
        model=os.getenv("PROCESSING_MODEL"),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }],
        response_format={"type": "json_object"}
    )

    # Parse the response
    response_text = response.choices[0].message.content
    data = json.loads(response_text)

    # Map category string to ExpenseType enum
    category_str = data.get("category", "OTHER")
    try:
        category = ExpenseType[category_str]
    except KeyError:
        category = ExpenseType.OTHER

    # Parse date
    date_data = data.get("date", {})
    expense_date = Date(
        day=date_data.get("day", today.day),
        month=date_data.get("month", today.month),
        year=date_data.get("year", today.year)
    )

    # Build and return the Expense object
    expense = Expense(
        expense_name=data.get("expense_name", "Unknown expense"),
        amount=data.get("amount", 0),
        date=expense_date,
        category=category
    )

    return expense


def parse_receipt(
    image_bytes: Optional[bytes] = None,
    text: Optional[str] = None,
    context: Optional[str] = None
) -> Expense:
    """
    Universal expense parser - handles text, images, or both.

    Args:
        image_bytes: Optional receipt image bytes
        text: Optional text description
        context: Optional additional context

    Returns:
        Expense object

    Raises:
        ValueError: If neither image_bytes nor text is provided
    """
    if not image_bytes and not text:
        raise ValueError("Must provide either image_bytes, text, or both")

    # If both are provided, use image parsing with text as context
    if image_bytes and text:
        combined_context = f"{context}\n{text}" if context else text
        return parse_image(image_bytes, context=combined_context)

    # Image only
    if image_bytes:
        return parse_image(image_bytes, context=context)

    # Text only
    return parse_text(text, context=context)
