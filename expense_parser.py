import base64
import json
from datetime import date
from typing import Optional

from endpoints import Endpoints
from output_schemas import Expense, ExpenseType, Date, Name


def parse_receipt(image_bytes: bytes, context: str) -> Expense:
    """
    Parse a receipt image and context string to extract expense data.
    
    Args:
        image_bytes: Raw bytes of the receipt image
        context: Context string with category, participants, project info
        
    Returns:
        Expense: Populated Expense object
    """
    # Initialize the OpenAI client
    endpoints = Endpoints()
    client = endpoints.openai_client
    
    # Encode image as base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Get today's date for fallback
    today = date.today()
    
    # Build the prompt
    prompt = f"""Analyze this receipt image and extract expense information.

Additional context provided by the user:
{context}

Extract the following information and return as JSON:

1. **expense_name**: A brief descriptive name for this expense (e.g., "Team lunch at Olive Garden", "Uber to airport"). If unclear, use "UNCLEAR".

2. **amount**: The total amount from the receipt as a number. If unclear or missing, use 0.

3. **date**: The date of the expense with day, month, and year as integers.
   - If the date is visible on the receipt, use that.
   - If no date is found on the receipt or in the context, use today's date: day={today.day}, month={today.month}, year={today.year}

4. **category**: One of these exact values based on what the expense is for:
   - "dinner" - dinner meals
   - "lunch" - lunch meals  
   - "breakfast" - breakfast meals 
   - "taxi/lyft/uber" - taxi or rideshare services
   - "hotel" - hotel accommodations
   - "technology (ie software subscription, ai subscriptions, etc.)" - tech/software
   - "airfare (airline tickets)" - airline tickets
   - "airport services (airport wifi, plane wifi, plane snacks, etc.)" - airport/plane services
   - "travel fees - usually from CWT, Wagonlit, or other travel agencies. DOES NOT INCLUDE AIRFARE or HOTEL." - travel agency fees
   - "other" - anything else or if unclear
   
   Use the context provided to help determine the category. If still unclear, use "other". Sort any food related
   expenses into either "dinner", "lunch", or "breakfast".

5. **participants**: List of people who participated (for meals). Extract from the context string.
   Each participant should have: first (string), last (string), company (string or null)
   If no participants are mentioned, return null for this field.

6. **project_name**: The project to charge this expense to. Extract from context. If not mentioned, return null.

Return ONLY valid JSON in this exact format:
{{
    "expense_name": "string",
    "amount": number,
    "date": {{"day": number, "month": number, "year": number}},
    "category": "category string from list above",
    "participants": [
        {{"first": "string", "last": "string", "company": "string or null"}}
    ] or null,
    "project_name": "string or null"
}}"""

    # Call GPT-5.2 with vision
    response = client.chat.completions.create(
        model="gpt-5.2-doc-parser",
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
    category_map = {
        "dinner": ExpenseType.DINNER,
        "lunch": ExpenseType.LUNCH,
        "breakfast": ExpenseType.BREAKFAST,
        "taxi/lyft/uber": ExpenseType.TAXI,
        "hotel": ExpenseType.HOTEL,
        "technology (ie software subscription, ai subscriptions, etc.)": ExpenseType.TECH,
        "airfare (airline tickets)": ExpenseType.AIRFARE,
        "airport services (airport wifi, plane wifi, plane snacks, etc.)": ExpenseType.AIRPORT_SERVICES,
        "travel fees - usually from CWT, Wagonlit, or other travel agencies. DOES NOT INCLUDE AIRFARE or HOTEL.": ExpenseType.TRAVEL_FEES_CWT,
        "other": ExpenseType.OTHER
    }
    
    # Get category, default to OTHER if not found
    category_str = data.get("category", "other").lower()
    category = category_map.get(category_str, ExpenseType.OTHER)
    
    # Parse date
    date_data = data.get("date", {})
    expense_date = Date(
        day=date_data.get("day", today.day),
        month=date_data.get("month", today.month),
        year=date_data.get("year", today.year)
    )
    
    # Parse participants
    participants = None
    if data.get("participants"):
        participants = [
            Name(
                first=p.get("first", "UNCLEAR"),
                last=p.get("last", "UNCLEAR"),
                company=p.get("company")
            )
            for p in data["participants"]
        ]
    
    # Build and return the Expense object
    expense = Expense(
        expense_name=data.get("expense_name", "UNCLEAR"),
        amount=data.get("amount", 0),
        date=expense_date,
        category=category,
        participants=participants,
        project_name=data.get("project_name")
    )
    
    return expense



