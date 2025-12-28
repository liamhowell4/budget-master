"""
Adaptive Card templates for Teams bot responses.
"""

import json
import uuid
from typing import Optional
from output_schemas import Expense, ExpenseType


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"


def format_date(date) -> str:
    """Format date object as readable string."""
    months = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    return f"{months[date.month]} {date.day}, {date.year}"


def get_category_emoji(category: ExpenseType) -> str:
    """Get emoji for expense category."""
    emoji_map = {
        ExpenseType.DINNER: "🍽️",
        ExpenseType.LUNCH: "🥪",
        ExpenseType.BREAKFAST: "🥐",
        ExpenseType.TAXI: "🚕",
        ExpenseType.HOTEL: "🏨",
        ExpenseType.TECH: "💻",
        ExpenseType.AIRFARE: "✈️",
        ExpenseType.AIRPORT_SERVICES: "🛫",
        ExpenseType.TRAVEL_FEES_CWT: "📋",
        ExpenseType.OTHER: "📦"
    }
    return emoji_map.get(category, "📦")


def _format_json(data: dict) -> str:
    """Format dict as indented JSON string."""
    return json.dumps(data, indent=2, default=str)


def create_expense_card(expense: Expense, include_feedback: bool = True) -> dict:
    """
    Create an Adaptive Card displaying the parsed expense.
    
    Args:
        expense: The parsed Expense object
        include_feedback: Whether to include thumbs up/down feedback buttons
    """
    category_emoji = get_category_emoji(expense.category)
    
    # Generate unique ID for this expense card (for feedback tracking)
    card_id = str(uuid.uuid4())[:8]
    
    # Build facts list
    facts = [
        {"title": "💰 Amount", "value": format_currency(expense.amount)},
        {"title": "📁 Category", "value": f"{category_emoji} {expense.category.value}"},
        {"title": "📅 Date", "value": format_date(expense.date)},
    ]
    
    # Add project if present
    if expense.project_name:
        facts.append({"title": "📂 Project", "value": expense.project_name})
    
    # Build participants text if present
    participants_text = None
    if expense.participants:
        participant_strings = []
        for p in expense.participants:
            name = f"{p.first} {p.last}"
            if p.company:
                name += f" ({p.company})"
            participant_strings.append(name)
        participants_text = ", ".join(participant_strings)
    
    # Build the card
    card = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "✅ Expense Parsed Successfully",
                "weight": "bolder",
                "size": "large",
                "color": "good"
            },
            {
                "type": "TextBlock",
                "text": expense.expense_name,
                "weight": "bolder",
                "size": "medium",
                "wrap": True
            },
            {
                "type": "FactSet",
                "facts": facts
            }
        ]
    }
    
    # Add participants section if present
    if participants_text:
        card["body"].append({
            "type": "TextBlock",
            "text": "👥 **Participants**",
            "weight": "bolder",
            "spacing": "medium"
        })
        card["body"].append({
            "type": "TextBlock",
            "text": participants_text,
            "wrap": True
        })
    
    # Add JSON toggle section
    expense_json = expense.model_dump()
    # Convert enum to string for JSON serialization
    expense_json["category"] = expense.category.value
    
    card["body"].append({
        "type": "Container",
        "spacing": "large",
        "items": [
            {
                "type": "TextBlock",
                "text": "📋 **Raw JSON**",
                "weight": "bolder"
            },
            {
                "type": "TextBlock",
                "text": f"```json\n{_format_json(expense_json)}\n```",
                "wrap": True,
                "fontType": "monospace",
                "size": "small"
            }
        ]
    })
    
    # Add feedback section with thumbs up/down buttons
    if include_feedback:
        card["body"].append({
            "type": "Container",
            "spacing": "medium",
            "separator": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": "Was this parsing accurate?",
                    "isSubtle": True,
                    "size": "small"
                },
                {
                    "type": "ActionSet",
                    "actions": [
                        {
                            "type": "Action.Submit",
                            "title": "👍",
                            "data": {
                                "action": "feedback",
                                "feedback": "positive",
                                "card_id": card_id,
                                "expense_name": expense.expense_name
                            }
                        },
                        {
                            "type": "Action.Submit",
                            "title": "👎",
                            "data": {
                                "action": "feedback",
                                "feedback": "negative",
                                "card_id": card_id,
                                "expense_name": expense.expense_name
                            }
                        }
                    ]
                }
            ]
        })
    
    return card


def create_feedback_response_card(feedback_type: str, expense_name: str) -> dict:
    """
    Create a simple card acknowledging the user's feedback.
    
    Args:
        feedback_type: Either "positive" or "negative"
        expense_name: Name of the expense that was rated
    """
    if feedback_type == "positive":
        emoji = "👍"
        message = "Thanks for the positive feedback!"
        color = "good"
    else:
        emoji = "👎"
        message = "Thanks for letting us know. We'll work on improving!"
        color = "warning"
    
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": f"{emoji} Feedback Received",
                "weight": "bolder",
                "size": "medium",
                "color": color
            },
            {
                "type": "TextBlock",
                "text": message,
                "wrap": True,
                "isSubtle": True
            }
        ]
    }


def create_error_card(error_message: str) -> dict:
    """Create an Adaptive Card for error display."""
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "❌ Error Processing Receipt",
                "weight": "bolder",
                "size": "large",
                "color": "attention"
            },
            {
                "type": "TextBlock",
                "text": "Something went wrong while processing your receipt:",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": error_message,
                "wrap": True,
                "color": "attention"
            },
            {
                "type": "TextBlock",
                "text": "Please try again with a clearer image, or contact support if the issue persists.",
                "wrap": True,
                "spacing": "medium",
                "isSubtle": True
            }
        ]
    }


def create_welcome_card() -> dict:
    """Create a welcome Adaptive Card for new users."""
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "🧾 Expense Receipt Bot",
                "weight": "bolder",
                "size": "extraLarge"
            },
            {
                "type": "TextBlock",
                "text": "Welcome! I can help you parse expense receipts and extract structured data.",
                "wrap": True,
                "spacing": "medium"
            },
            {
                "type": "TextBlock",
                "text": "**How to use:**",
                "weight": "bolder",
                "spacing": "large"
            },
            {
                "type": "TextBlock",
                "text": "1️⃣ Send me a photo of your receipt",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": "2️⃣ Add a caption with context (optional but helpful):",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": "• Who was there (e.g., \"lunch with John Smith from Acme Corp\")\n• Project name (e.g., \"project Alpha\")\n• Expense category if not obvious",
                "wrap": True,
                "isSubtle": True
            },
            {
                "type": "TextBlock",
                "text": "3️⃣ I'll extract and return the expense data as JSON",
                "wrap": True
            },
            {
                "type": "Container",
                "style": "emphasis",
                "spacing": "large",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "**Example caption:**",
                        "weight": "bolder"
                    },
                    {
                        "type": "TextBlock",
                        "text": "_\"Team lunch with Sarah Jones and Mike Chen (both from Contoso), project Omega\"_",
                        "wrap": True,
                        "isSubtle": True
                    }
                ]
            }
        ]
    }


