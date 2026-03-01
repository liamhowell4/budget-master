#!/usr/bin/env python3
"""
MCP Expense Server - Exposes expense tracking tools via Model Context Protocol.

This server runs as a subprocess and communicates via stdio (stdin/stdout).
It provides tools for Claude to use:
1. save_expense - Save a parsed expense to Firebase
2. get_budget_status - Check budget status and get warnings
3. get_categories - List all valid expense categories
4. update_expense - Update an existing expense
5. delete_expense - Delete an expense
6. get_recent_expenses - Get recent expenses from Firebase
7. search_expenses - Search expenses by name

Usage:
    python backend/mcp/expense_server.py
    (Typically spawned by the MCP client, not run directly)
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Any, Optional

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import backend modules
from backend.firebase_client import FirebaseClient
from backend.budget_manager import BudgetManager
from backend.output_schemas import Expense, ExpenseType, Date, RecurringExpense, FrequencyType
from backend.exceptions import DocumentNotFoundError, InvalidCategoryError


# Initialize global Firebase client for categories (read-only, shared)
# User-scoped clients are created per-request based on user_id
_global_firebase = FirebaseClient()

# Create MCP server
server = Server("expense-tracker-mcp")


# Common schema properties
AUTH_TOKEN_PROPERTY = {"type": "string"}

DATE_SCHEMA = {
    "type": "object",
    "properties": {
        "day": {"type": "integer"},
        "month": {"type": "integer"},
        "year": {"type": "integer"}
    },
    "required": ["day", "month", "year"]
}


def verify_token_and_get_uid(auth_token: str) -> str:
    """
    Verify Firebase Auth token and extract user ID.

    Firebase Auth does the cryptographic verification - we just read the result.

    Args:
        auth_token: Firebase ID token from client

    Returns:
        User ID (uid) from the verified token

    Raises:
        ValueError: If token is invalid or verification fails
    """
    import firebase_admin.auth as firebase_auth

    try:
        # Firebase verifies: signature, expiry, issuer, audience
        decoded_token = firebase_auth.verify_id_token(auth_token)
        return decoded_token["uid"]
    except firebase_auth.InvalidIdTokenError:
        raise ValueError("Invalid authentication token")
    except firebase_auth.ExpiredIdTokenError:
        raise ValueError("Authentication token has expired")
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")


def get_user_firebase(arguments: dict) -> FirebaseClient:
    """
    Get a user-scoped FirebaseClient from tool arguments.

    Verifies the auth token with Firebase Auth before creating the client.

    Args:
        arguments: Tool arguments dict containing 'auth_token'

    Returns:
        FirebaseClient scoped to the verified user

    Raises:
        ValueError: If auth_token is missing or invalid
    """
    auth_token = arguments.get("auth_token")
    if not auth_token:
        raise ValueError("auth_token is required for authentication")

    # Firebase Auth verifies the token and gives us the uid
    user_id = verify_token_and_get_uid(auth_token)
    return FirebaseClient.for_user(user_id)


def get_user_budget_manager(arguments: dict) -> BudgetManager:
    """
    Get a user-scoped BudgetManager from tool arguments.

    Verifies the auth token with Firebase Auth before creating the manager.

    Args:
        arguments: Tool arguments dict containing 'auth_token'

    Returns:
        BudgetManager scoped to the verified user
    """
    firebase = get_user_firebase(arguments)
    return BudgetManager(firebase)


def validate_category(category_str: str, firebase: FirebaseClient) -> None:
    """
    Validate that a category exists for the user.

    Args:
        category_str: Category ID to validate
        firebase: User-scoped FirebaseClient

    Raises:
        InvalidCategoryError: If category does not exist
    """
    # Check if user has custom categories set up
    if firebase.has_categories_setup():
        categories = firebase.get_user_categories()
        valid_ids = [c.get("category_id") for c in categories]
        if category_str not in valid_ids:
            raise InvalidCategoryError(category_str)
    else:
        # Fallback to ExpenseType enum for backward compatibility
        try:
            ExpenseType[category_str]
        except KeyError:
            raise InvalidCategoryError(category_str)


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List available tools for expense tracking.

    Returns:
        List of Tool objects that Claude can call
    """
    return [
        Tool(
            name="save_expense",
            description=(
                "Save a parsed expense to Firebase Firestore. "
                "Call this after extracting expense information from user input. "
                "Returns the saved expense ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "name": {
                        "type": "string",
                        "description": "Descriptive name for the expense (e.g., 'Starbucks coffee', 'Chipotle lunch')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Dollar amount of the expense - positive for spending, negative for refunds/reimbursements (e.g., 5.50, 15.00, -20.00)"
                    },
                    "date": {**DATE_SCHEMA, "description": "Date of the expense"},
                    "category": {
                        "type": "string",
                        "description": "Expense category key (e.g., 'FOOD_OUT', 'COFFEE', 'GROCERIES'). Use get_categories to see all valid options.",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token", "name", "amount", "date", "category"]
            }
        ),
        Tool(
            name="get_budget_status",
            description=(
                "Check budget status after saving an expense. "
                "Returns budget warnings if user is approaching or over budget limits. "
                "Call this after save_expense to inform the user about their budget status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "category": {
                        "type": "string",
                        "description": "The expense category to check (e.g., 'FOOD_OUT', 'COFFEE')",
                        "enum": [e.name for e in ExpenseType]
                    },
                    "amount": {
                        "type": "number",
                        "description": "The expense amount that was just added"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year for budget calculation"
                    },
                    "month": {
                        "type": "integer",
                        "description": "Month for budget calculation (1-12)",
                        "minimum": 1,
                        "maximum": 12
                    }
                },
                "required": ["auth_token", "category", "amount", "year", "month"]
            }
        ),
        Tool(
            name="get_categories",
            description=(
                "Get all valid expense categories for the user. "
                "Use this to understand which category to assign to an expense."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY
                },
                "required": ["auth_token"]
            }
        ),
        Tool(
            name="update_expense",
            description=(
                "Update an existing expense's fields. "
                "Use this when the user wants to correct or modify a previous expense. "
                "You can update name, amount, date, and/or category."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "expense_id": {
                        "type": "string",
                        "description": "The Firebase document ID of the expense to update"
                    },
                    "name": {
                        "type": "string",
                        "description": "New expense name (optional)"
                    },
                    "amount": {
                        "type": "number",
                        "description": "New amount - positive for spending, negative for refunds (optional)"
                    },
                    "date": {**DATE_SCHEMA, "description": "New date (optional)"},
                    "category": {
                        "type": "string",
                        "description": "New category (optional)",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token", "expense_id"]
            }
        ),
        Tool(
            name="delete_expense",
            description=(
                "Delete an expense from Firebase. "
                "Use this when the user confirms they want to remove an expense. "
                "Always confirm with the user before calling this tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "expense_id": {
                        "type": "string",
                        "description": "The Firebase document ID of the expense to delete"
                    }
                },
                "required": ["auth_token", "expense_id"]
            }
        ),
        Tool(
            name="get_recent_expenses",
            description=(
                "Get recent expenses from Firebase (last 7 days or 20 expenses, whichever is fewer). "
                "Use this when the user asks to see their recent purchases or recent activity. "
                "Returns expenses sorted by most recent first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of expenses to return (default 20)",
                        "minimum": 1,
                        "maximum": 50
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (optional)",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token"]
            }
        ),
        Tool(
            name="search_expenses",
            description=(
                "Search for expenses by name using substring matching. "
                "Searches current month by default, or specify a date range. "
                "Also supports filtering by category."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "query": {
                        "type": "string",
                        "description": "Text to search for in expense names (case-insensitive)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (optional)",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token", "query"]
            }
        ),
        Tool(
            name="create_recurring_expense",
            description=(
                "Create a recurring expense template for subscriptions, rent, bills, etc. "
                "The system will automatically create pending expenses on the specified schedule. "
                "Supports monthly (on specific day), weekly (on specific weekday), biweekly, and yearly frequencies. "
                "NOTE: Recurring expenses must have positive amounts only (no negative/refund recurring expenses)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "name": {
                        "type": "string",
                        "description": "Name of the recurring expense (e.g., 'Libro.fm subscription', 'Rent', 'Netflix')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount of the recurring expense (must be positive - no negative recurring expenses)",
                        "minimum": 0.01
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category",
                        "enum": [e.name for e in ExpenseType]
                    },
                    "frequency": {
                        "type": "string",
                        "description": "How often the expense recurs",
                        "enum": ["monthly", "weekly", "biweekly", "yearly"]
                    },
                    "day_of_month": {
                        "type": "integer",
                        "description": "Day of month (1-31) for monthly or yearly recurring expenses. Required if frequency is 'monthly' or 'yearly'.",
                        "minimum": 1,
                        "maximum": 31
                    },
                    "month_of_year": {
                        "type": "integer",
                        "description": "Month of year (1=January, 12=December) for yearly recurring expenses. Required if frequency is 'yearly'.",
                        "minimum": 1,
                        "maximum": 12
                    },
                    "day_of_week": {
                        "type": "integer",
                        "description": "Day of week (0=Monday, 6=Sunday) for weekly/biweekly expenses. Required if frequency is 'weekly' or 'biweekly'.",
                        "minimum": 0,
                        "maximum": 6
                    },
                    "last_of_month": {
                        "type": "boolean",
                        "description": "Set to true if user wants last day of month (ignores day_of_month)",
                        "default": False
                    }
                },
                "required": ["auth_token", "name", "amount", "category", "frequency"]
            }
        ),
        Tool(
            name="list_recurring_expenses",
            description=(
                "Get all active recurring expense templates. "
                "Use this when the user asks to see their subscriptions, recurring bills, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "active_only": {
                        "type": "boolean",
                        "description": "Only show active recurring expenses (default true)",
                        "default": True
                    }
                },
                "required": ["auth_token"]
            }
        ),
        Tool(
            name="delete_recurring_expense",
            description=(
                "Delete/deactivate a recurring expense template. "
                "This will stop future pending expenses from being created. "
                "Always confirm with the user before calling this tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "template_id": {
                        "type": "string",
                        "description": "The Firebase document ID of the recurring expense template to delete"
                    }
                },
                "required": ["auth_token", "template_id"]
            }
        ),
        Tool(
            name="query_expenses",
            description=(
                "Query expenses with flexible filtering by date range, category, and amount. "
                "Returns detailed expense list with totals. "
                "Date range can span up to 12 months (warns if >3 months)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "start_date": {**DATE_SCHEMA, "description": "Start date (inclusive)"},
                    "end_date": {**DATE_SCHEMA, "description": "End date (inclusive)"},
                    "category": {
                        "type": "string",
                        "description": "Filter by specific category (optional)",
                        "enum": [e.name for e in ExpenseType]
                    },
                    "min_amount": {
                        "type": "number",
                        "description": "Filter expenses above this amount (optional)"
                    }
                },
                "required": ["auth_token", "start_date", "end_date"]
            }
        ),
        Tool(
            name="get_spending_by_category",
            description=(
                "Get spending breakdown by category for a date range. "
                "Shows how much was spent in each category with transaction counts. "
                "Useful for 'How much did I spend on food last week?' type questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "start_date": {**DATE_SCHEMA, "description": "Start date (inclusive)"},
                    "end_date": {**DATE_SCHEMA, "description": "End date (inclusive)"}
                },
                "required": ["auth_token", "start_date", "end_date"]
            }
        ),
        Tool(
            name="get_spending_summary",
            description=(
                "Get overall spending summary for a date range. "
                "Returns total spending, transaction count, and average per transaction. "
                "Good for general spending questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "start_date": {**DATE_SCHEMA, "description": "Start date (inclusive)"},
                    "end_date": {**DATE_SCHEMA, "description": "End date (inclusive)"}
                },
                "required": ["auth_token", "start_date", "end_date"]
            }
        ),
        Tool(
            name="get_budget_remaining",
            description=(
                "Get remaining budget for all categories or a specific category. "
                "Shows current spending, cap, percentage used, and amount remaining. "
                "Formatted like the 'status' command."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "category": {
                        "type": "string",
                        "description": "Specific category to check (optional - if omitted, shows all categories)",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token"]
            }
        ),
        Tool(
            name="compare_periods",
            description=(
                "Compare spending between two time periods. "
                "Shows difference in spending (both absolute dollar amount and percentage change). "
                "Useful for 'compare this month to last month' type questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "period1_start": {**DATE_SCHEMA, "description": "Period 1 start date"},
                    "period1_end": {**DATE_SCHEMA, "description": "Period 1 end date"},
                    "period2_start": {**DATE_SCHEMA, "description": "Period 2 start date"},
                    "period2_end": {**DATE_SCHEMA, "description": "Period 2 end date"},
                    "category": {
                        "type": "string",
                        "description": "Optional category to compare (if omitted, compares total spending)",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token", "period1_start", "period1_end", "period2_start", "period2_end"]
            }
        ),
        Tool(
            name="get_largest_expenses",
            description=(
                "Get the largest expenses for a date range. "
                "Returns top 3 expenses by amount with details. "
                "Useful for 'what was my biggest expense' type questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": AUTH_TOKEN_PROPERTY,
                    "start_date": {**DATE_SCHEMA, "description": "Start date (inclusive)"},
                    "end_date": {**DATE_SCHEMA, "description": "End date (inclusive)"},
                    "category": {
                        "type": "string",
                        "description": "Optional category filter",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["auth_token", "start_date", "end_date"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool execution requests.

    Args:
        name: Tool name to execute
        arguments: Tool arguments as dictionary

    Returns:
        List of TextContent with tool results
    """
    try:
        if name == "save_expense":
            return await _save_expense(arguments)
        elif name == "get_budget_status":
            return await _get_budget_status(arguments)
        elif name == "get_categories":
            return await _get_categories(arguments)
        elif name == "update_expense":
            return await _update_expense(arguments)
        elif name == "delete_expense":
            return await _delete_expense(arguments)
        elif name == "get_recent_expenses":
            return await _get_recent_expenses(arguments)
        elif name == "search_expenses":
            return await _search_expenses(arguments)
        elif name == "create_recurring_expense":
            return await _create_recurring_expense(arguments)
        elif name == "list_recurring_expenses":
            return await _list_recurring_expenses(arguments)
        elif name == "delete_recurring_expense":
            return await _delete_recurring_expense(arguments)
        elif name == "query_expenses":
            return await _query_expenses(arguments)
        elif name == "get_spending_by_category":
            return await _get_spending_by_category(arguments)
        elif name == "get_spending_summary":
            return await _get_spending_summary(arguments)
        elif name == "get_budget_remaining":
            return await _get_budget_remaining(arguments)
        elif name == "compare_periods":
            return await _compare_periods(arguments)
        elif name == "get_largest_expenses":
            return await _get_largest_expenses(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        # Return error as TextContent
        import traceback
        error_msg = f"Error executing {name}: {str(e)}\n{traceback.format_exc()}"
        return [TextContent(type="text", text=error_msg)]


async def _save_expense(arguments: dict) -> list[TextContent]:
    """
    Save an expense to Firebase.

    Args:
        arguments: {
            "name": str,
            "amount": float,
            "date": {"day": int, "month": int, "year": int},
            "category": str
        }

    Returns:
        TextContent with expense_id
    """
    # Parse arguments
    expense_name = arguments["name"]
    amount = float(arguments["amount"])
    date_dict = arguments["date"]
    category_str = arguments["category"]

    # Create Date object
    expense_date = Date(
        day=date_dict["day"],
        month=date_dict["month"],
        year=date_dict["year"]
    )

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Validate category against user's categories
    try:
        validate_category(category_str, firebase)
    except InvalidCategoryError:
        return [TextContent(
            type="text",
            text=f"Error: Invalid category '{category_str}'. Use get_categories to see valid options."
        )]

    # Parse category for backward compatibility with ExpenseType
    # If user has custom categories, we still try to match to ExpenseType
    # but fall back to OTHER if not found
    try:
        category = ExpenseType[category_str]
    except KeyError:
        # Custom category not in ExpenseType, use OTHER for Pydantic model
        # but save the actual category_str to Firestore
        category = ExpenseType.OTHER

    # Create Expense object
    expense = Expense(
        expense_name=expense_name,
        amount=amount,
        date=expense_date,
        category=category
    )

    # Save expense - override category in save to use string
    expense_id = firebase.save_expense(expense, input_type="mcp", category_str=category_str)

    # Return success response
    result = {
        "success": True,
        "expense_id": expense_id,
        "expense_name": expense_name,
        "amount": amount,
        "category": category_str
    }

    import json
    return [TextContent(type="text", text=json.dumps(result))]


async def _get_budget_status(arguments: dict) -> list[TextContent]:
    """
    Get budget status and warnings.

    Args:
        arguments: {
            "category": str,
            "amount": float,
            "year": int,
            "month": int
        }

    Returns:
        TextContent with budget warning message (if any)
    """
    import json

    category_str = arguments["category"]
    amount = float(arguments["amount"])
    year = int(arguments["year"])
    month = int(arguments["month"])

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Validate category
    try:
        validate_category(category_str, firebase)
    except InvalidCategoryError:
        return [TextContent(
            type="text",
            text=f"Error: Invalid category '{category_str}'"
        )]

    # Get user-scoped budget manager and get warning
    user_budget_manager = get_user_budget_manager(arguments)
    warning = user_budget_manager.get_budget_warning_for_category(
        category_id=category_str,
        amount=amount,
        year=year,
        month=month
    )

    # Return warning (empty string if no warnings)
    result = {
        "budget_warning": warning if warning else ""
    }

    return [TextContent(type="text", text=json.dumps(result))]


async def _get_categories(arguments: dict) -> list[TextContent]:
    """
    Get all valid expense categories for the user.

    Args:
        arguments: {"auth_token": str}

    Returns:
        TextContent with category list
    """
    import json

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Check if user has custom categories
    if firebase.has_categories_setup():
        user_categories = firebase.get_user_categories()
        categories = []
        for cat in user_categories:
            categories.append({
                "key": cat.get("category_id"),
                "display_name": cat.get("display_name", cat.get("category_id")),
                "description": cat.get("description", "")
            })
    else:
        # Fallback to ExpenseType enum for backward compatibility
        categories = []
        for expense_type in ExpenseType:
            categories.append({
                "key": expense_type.name,
                "description": expense_type.value
            })

    return [TextContent(type="text", text=json.dumps({"categories": categories}))]


async def _update_expense(arguments: dict) -> list[TextContent]:
    """
    Update an existing expense.

    Args:
        arguments: {
            "expense_id": str,
            "name": str (optional),
            "amount": float (optional),
            "date": dict (optional),
            "category": str (optional)
        }

    Returns:
        TextContent with success/error message
    """
    expense_id = arguments["expense_id"]

    # Prepare optional fields
    expense_name = arguments.get("name")
    amount = arguments.get("amount")
    date_dict = arguments.get("date")
    category_str = arguments.get("category")

    # Convert date dict to Date object if provided
    date_obj = None
    if date_dict:
        date_obj = Date(
            day=date_dict["day"],
            month=date_dict["month"],
            year=date_dict["year"]
        )

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Validate category if provided
    if category_str:
        try:
            validate_category(category_str, firebase)
        except InvalidCategoryError:
            return [TextContent(
                type="text",
                text=f"Error: Invalid category '{category_str}'"
            )]

    # Convert category string to ExpenseType if provided (for backward compat)
    category_obj = None
    if category_str:
        try:
            category_obj = ExpenseType[category_str]
        except KeyError:
            # Custom category - update directly using string
            pass

    # Update expense
    try:
        firebase.update_expense(
            expense_id=expense_id,
            expense_name=expense_name,
            amount=amount,
            date=date_obj,
            category=category_obj,
            category_str=category_str  # Pass string for custom categories
        )
    except DocumentNotFoundError:
        return [TextContent(
            type="text",
            text=f"Error: Expense {expense_id} not found"
        )]

    # Get updated expense to return details
    updated_expense = firebase.get_expense_by_id(expense_id)

    result = {
        "success": True,
        "expense_id": expense_id,
        "expense_name": updated_expense.get("expense_name"),
        "amount": updated_expense.get("amount"),
        "category": updated_expense.get("category")
    }

    import json
    return [TextContent(type="text", text=json.dumps(result))]


async def _delete_expense(arguments: dict) -> list[TextContent]:
    """
    Delete an expense.

    Args:
        arguments: {
            "expense_id": str
        }

    Returns:
        TextContent with success/error message
    """
    expense_id = arguments["expense_id"]

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get expense details before deleting (for confirmation message)
    expense = firebase.get_expense_by_id(expense_id)

    if not expense:
        return [TextContent(
            type="text",
            text=f"Error: Expense {expense_id} not found"
        )]

    # Delete expense
    try:
        firebase.delete_expense(expense_id)
    except DocumentNotFoundError:
        return [TextContent(
            type="text",
            text=f"Error: Failed to delete expense {expense_id}"
        )]

    result = {
        "success": True,
        "expense_id": expense_id,
        "deleted_expense": {
            "name": expense.get("expense_name"),
            "amount": expense.get("amount"),
            "category": expense.get("category")
        }
    }

    import json
    return [TextContent(type="text", text=json.dumps(result))]


async def _get_recent_expenses(arguments: dict) -> list[TextContent]:
    """
    Get recent expenses from Firebase.

    Args:
        arguments: {
            "limit": int (optional, default 20),
            "category": str (optional)
        }

    Returns:
        TextContent with list of recent expenses
    """
    limit = arguments.get("limit", 20)
    category_str = arguments.get("category")

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Parse category if provided
    category_obj = None
    if category_str:
        try:
            category_obj = ExpenseType[category_str]
        except KeyError:
            return [TextContent(
                type="text",
                text=f"Error: Invalid category '{category_str}'"
            )]

    # Get recent expenses
    expenses = firebase.get_recent_expenses_from_db(
        limit=limit,
        category=category_obj
    )

    # Format expenses for response
    formatted_expenses = []
    for exp in expenses:
        formatted_expenses.append({
            "id": exp.get("id"),
            "name": exp.get("expense_name"),
            "amount": exp.get("amount"),
            "category": exp.get("category"),
            "date": exp.get("date")
        })

    result = {
        "count": len(formatted_expenses),
        "expenses": formatted_expenses
    }

    import json
    return [TextContent(type="text", text=json.dumps(result))]


async def _search_expenses(arguments: dict) -> list[TextContent]:
    """
    Search expenses by name.

    Args:
        arguments: {
            "query": str,
            "category": str (optional)
        }

    Returns:
        TextContent with list of matching expenses
    """
    query = arguments["query"]
    category_str = arguments.get("category")

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Parse category if provided
    category_obj = None
    if category_str:
        try:
            category_obj = ExpenseType[category_str]
        except KeyError:
            return [TextContent(
                type="text",
                text=f"Error: Invalid category '{category_str}'"
            )]

    # Search expenses (defaults to current month)
    expenses = firebase.search_expenses_in_db(
        text_query=query,
        category=category_obj
    )

    # Format expenses for response
    formatted_expenses = []
    for exp in expenses:
        formatted_expenses.append({
            "id": exp.get("id"),
            "name": exp.get("expense_name"),
            "amount": exp.get("amount"),
            "category": exp.get("category"),
            "date": exp.get("date")
        })

    result = {
        "query": query,
        "count": len(formatted_expenses),
        "expenses": formatted_expenses
    }

    import json
    return [TextContent(type="text", text=json.dumps(result))]


async def _create_recurring_expense(arguments: dict) -> list[TextContent]:
    """
    Create a recurring expense template.

    Args:
        arguments: {
            "name": str,
            "amount": float,
            "category": str,
            "frequency": str ("monthly", "weekly", "biweekly", "yearly"),
            "day_of_month": int (optional, for monthly/yearly),
            "day_of_week": int (optional, for weekly/biweekly),
            "month_of_year": int (optional, for yearly),
            "last_of_month": bool (optional)
        }

    Returns:
        TextContent with template_id and confirmation
    """
    import json
    from backend.recurring_manager import get_today_in_user_timezone

    name = arguments["name"]
    amount = arguments["amount"]
    category_str = arguments["category"]
    frequency_str = arguments["frequency"]
    day_of_month = arguments.get("day_of_month")
    day_of_week = arguments.get("day_of_week")
    month_of_year = arguments.get("month_of_year")
    last_of_month = arguments.get("last_of_month", False)

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Validate category against user's categories
    try:
        validate_category(category_str, firebase)
    except InvalidCategoryError:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Invalid category: {category_str}"
        }))]

    # Convert category string to ExpenseType enum (for Pydantic model)
    try:
        category = ExpenseType[category_str]
    except KeyError:
        # Custom category - use OTHER for model, actual category saved as string
        category = ExpenseType.OTHER

    # Convert frequency string to FrequencyType enum
    try:
        frequency = FrequencyType(frequency_str)
    except ValueError:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Invalid frequency: {frequency_str}"
        }))]

    # Validate day_of_month for monthly frequency
    if frequency == FrequencyType.MONTHLY and not last_of_month and day_of_month is None:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "day_of_month is required for monthly recurring expenses"
        }))]

    # Validate day_of_month and month_of_year for yearly frequency
    if frequency == FrequencyType.YEARLY:
        if month_of_year is None:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "month_of_year is required for yearly recurring expenses"
            }))]
        if not last_of_month and day_of_month is None:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "day_of_month is required for yearly recurring expenses"
            }))]

    # Validate day_of_week for weekly/biweekly
    if frequency in [FrequencyType.WEEKLY, FrequencyType.BIWEEKLY] and day_of_week is None:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "day_of_week is required for weekly/biweekly recurring expenses"
        }))]

    # Get today's date for last_reminded (will check if we need to create pending expense)
    today = get_today_in_user_timezone()
    today_date = Date(day=today.day, month=today.month, year=today.year)

    # Create recurring expense object
    recurring = RecurringExpense(
        expense_name=name,
        amount=amount,
        category=category,
        frequency=frequency,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
        month_of_year=month_of_year,
        last_of_month=last_of_month,
        last_reminded=None,  # Will be set when first pending expense is created
        last_user_action=today_date,  # Set to today to avoid immediate retroactive pending
        active=True
    )

    # Save recurring expense with custom category string
    template_id = firebase.save_recurring_expense(recurring, category_str=category_str)

    result = {
        "success": True,
        "template_id": template_id,
        "expense_name": name,
        "amount": amount,
        "category": category_str,
        "frequency": frequency_str,
        "message": f"Created recurring expense: {name} (${amount:.2f} {frequency_str})"
    }

    # Check if we should immediately log the current period's expense
    from backend.recurring_manager import RecurringManager
    should_log, expense_date = RecurringManager.should_log_initial_expense(recurring, today)

    if should_log and expense_date:
        expense = Expense(
            expense_name=name,
            amount=amount,
            date=Date(day=expense_date.day, month=expense_date.month, year=expense_date.year),
            category=category
        )
        expense_id = firebase.save_expense(expense, input_type="recurring", category_str=category_str)

        # Update recurring template to prevent duplicate pending creation
        firebase.update_recurring_expense(template_id, {
            "last_reminded": {
                "day": today.day,
                "month": today.month,
                "year": today.year
            },
            "last_user_action": {
                "day": today.day,
                "month": today.month,
                "year": today.year
            }
        })

        result["initial_expense_logged"] = True
        result["expense_id"] = expense_id
        result["expense_date"] = f"{expense_date.year}-{expense_date.month:02d}-{expense_date.day:02d}"
        result["message"] += f". Also logged expense for {expense_date.strftime('%b %d, %Y')} (${amount:.2f})"

    return [TextContent(type="text", text=json.dumps(result))]


async def _list_recurring_expenses(arguments: dict) -> list[TextContent]:
    """
    List all recurring expense templates.

    Args:
        arguments: {
            "active_only": bool (optional, default True)
        }

    Returns:
        TextContent with list of recurring expenses
    """
    import json

    active_only = arguments.get("active_only", True)

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get recurring expenses from Firebase
    recurring_list = firebase.get_all_recurring_expenses(active_only=active_only)

    # Format for response
    formatted_expenses = []
    for recurring in recurring_list:
        exp_dict = {
            "template_id": recurring.template_id,
            "expense_name": recurring.expense_name,
            "amount": recurring.amount,
            "category": recurring.category.name,
            "frequency": recurring.frequency.value,
            "active": recurring.active
        }

        if recurring.frequency == FrequencyType.MONTHLY:
            if recurring.last_of_month:
                exp_dict["schedule"] = "last day of month"
            else:
                exp_dict["schedule"] = f"day {recurring.day_of_month} of month"
        elif recurring.frequency in [FrequencyType.WEEKLY, FrequencyType.BIWEEKLY]:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_name = days[recurring.day_of_week] if recurring.day_of_week is not None else "Unknown"
            exp_dict["schedule"] = day_name

        formatted_expenses.append(exp_dict)

    result = {
        "count": len(formatted_expenses),
        "recurring_expenses": formatted_expenses
    }

    return [TextContent(type="text", text=json.dumps(result))]


async def _delete_recurring_expense(arguments: dict) -> list[TextContent]:
    """
    Delete/deactivate a recurring expense template.

    Args:
        arguments: {
            "template_id": str
        }

    Returns:
        TextContent with confirmation
    """
    import json

    template_id = arguments["template_id"]

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get the expense first to return details
    recurring = firebase.get_recurring_expense(template_id)

    if not recurring:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Recurring expense {template_id} not found"
        }))]

    # Delete the recurring expense
    firebase.delete_recurring_expense(template_id)

    result = {
        "success": True,
        "template_id": template_id,
        "expense_name": recurring.expense_name,
        "amount": recurring.amount,
        "message": f"Deleted recurring expense: {recurring.expense_name} (${recurring.amount:.2f})"
    }

    return [TextContent(type="text", text=json.dumps(result))]


async def _query_expenses(arguments: dict) -> list[TextContent]:
    """
    Query expenses with flexible filtering.

    Args:
        arguments: {
            "start_date": {day, month, year},
            "end_date": {day, month, year},
            "category": str (optional),
            "min_amount": float (optional)
        }

    Returns:
        TextContent with expense list and totals
    """
    import json
    from datetime import date as date_type

    # Parse dates
    start_date_dict = arguments["start_date"]
    end_date_dict = arguments["end_date"]
    start_date = Date(
        day=start_date_dict["day"],
        month=start_date_dict["month"],
        year=start_date_dict["year"]
    )
    end_date = Date(
        day=end_date_dict["day"],
        month=end_date_dict["month"],
        year=end_date_dict["year"]
    )

    # Check date range (warn if >3 months, block if >12 months)
    start_obj = date_type(start_date.year, start_date.month, start_date.day)
    end_obj = date_type(end_date.year, end_date.month, end_date.day)
    days_diff = (end_obj - start_obj).days

    if days_diff > 365:
        return [TextContent(type="text", text=json.dumps({
            "error": "Date range exceeds 12 months limit. Please use a shorter range."
        }))]

    warning = ""
    if days_diff > 90:  # ~3 months
        warning = "Query spans more than 3 months - results may take longer to load."

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get category filter
    category = None
    if "category" in arguments and arguments["category"]:
        category = ExpenseType[arguments["category"]]

    # Get expenses
    expenses = firebase.get_expenses_in_date_range(start_date, end_date, category)

    # Filter by min_amount if provided
    min_amount = arguments.get("min_amount")
    if min_amount is not None:
        expenses = [exp for exp in expenses if exp.get("amount", 0) >= min_amount]

    # Calculate totals
    total = sum(exp.get("amount", 0) for exp in expenses)
    count = len(expenses)

    # Format result
    result = {
        "expenses": expenses,
        "total": total,
        "count": count,
        "start_date": start_date_dict,
        "end_date": end_date_dict
    }

    if warning:
        result["warning"] = warning

    return [TextContent(type="text", text=json.dumps(result))]


async def _get_spending_by_category(arguments: dict) -> list[TextContent]:
    """
    Get spending breakdown by category.

    Args:
        arguments: {
            "start_date": {day, month, year},
            "end_date": {day, month, year}
        }

    Returns:
        TextContent with category breakdown
    """
    import json

    # Parse dates
    start_date_dict = arguments["start_date"]
    end_date_dict = arguments["end_date"]
    start_date = Date(
        day=start_date_dict["day"],
        month=start_date_dict["month"],
        year=start_date_dict["year"]
    )
    end_date = Date(
        day=end_date_dict["day"],
        month=end_date_dict["month"],
        year=end_date_dict["year"]
    )

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get category totals
    category_totals = firebase.get_spending_by_category(start_date, end_date)

    # Get detailed expenses for transaction counts
    expenses = firebase.get_expenses_in_date_range(start_date, end_date)

    # Count transactions per category
    category_counts = {}
    for exp in expenses:
        cat = exp.get("category", "OTHER")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Build detailed breakdown with transaction names
    breakdown = []
    for category, total in category_totals.items():
        cat_expenses = [e for e in expenses if e.get("category") == category]

        breakdown.append({
            "category": category,
            "total": total,
            "count": category_counts.get(category, 0),
            "transactions": [
                {
                    "name": e.get("expense_name"),
                    "amount": e.get("amount"),
                    "date": e.get("date")
                }
                for e in cat_expenses
            ]
        })

    # Sort by total (highest first)
    breakdown.sort(key=lambda x: x["total"], reverse=True)

    # Overall total
    overall_total = sum(category_totals.values())

    result = {
        "breakdown": breakdown,
        "total": overall_total,
        "start_date": start_date_dict,
        "end_date": end_date_dict
    }

    return [TextContent(type="text", text=json.dumps(result))]


async def _get_spending_summary(arguments: dict) -> list[TextContent]:
    """
    Get overall spending summary.

    Args:
        arguments: {
            "start_date": {day, month, year},
            "end_date": {day, month, year}
        }

    Returns:
        TextContent with summary stats
    """
    import json

    # Parse dates
    start_date_dict = arguments["start_date"]
    end_date_dict = arguments["end_date"]
    start_date = Date(
        day=start_date_dict["day"],
        month=start_date_dict["month"],
        year=start_date_dict["year"]
    )
    end_date = Date(
        day=end_date_dict["day"],
        month=end_date_dict["month"],
        year=end_date_dict["year"]
    )

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get spending data
    summary = firebase.get_total_spending_for_range(start_date, end_date)

    # Calculate average per transaction
    average = summary["total"] / summary["count"] if summary["count"] > 0 else 0

    result = {
        "total": summary["total"],
        "count": summary["count"],
        "average_per_transaction": average,
        "start_date": start_date_dict,
        "end_date": end_date_dict
    }

    return [TextContent(type="text", text=json.dumps(result))]


async def _get_budget_remaining(arguments: dict) -> list[TextContent]:
    """
    Get budget remaining for categories (status-style format).

    Args:
        arguments: {
            "category": str (optional)
        }

    Returns:
        TextContent with budget status
    """
    import json
    from datetime import datetime
    import os, pytz

    # Get current month/year
    user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    year = now.year
    month = now.month

    # Get user-scoped Firebase client and budget manager
    firebase = get_user_firebase(arguments)
    user_budget_manager = get_user_budget_manager(arguments)

    # Get all budget caps
    all_caps = {}
    for expense_type in ExpenseType:
        cap = firebase.get_budget_cap(expense_type.name)
        if cap:
            all_caps[expense_type.name] = cap

    # Get total cap
    total_cap = firebase.get_budget_cap("TOTAL")

    # Calculate spending per category
    category_spending = {}
    for expense_type in ExpenseType:
        spending = user_budget_manager.calculate_monthly_spending(
            category=expense_type,
            year=year,
            month=month
        )
        category_spending[expense_type.name] = spending

    # Check if specific category requested
    specific_category = arguments.get("category")

    if specific_category:
        # Just return this category
        cap = all_caps.get(specific_category, 0)
        spending = category_spending.get(specific_category, 0)
        percentage = (spending / cap * 100) if cap > 0 else 0
        remaining = cap - spending

        result = {
            "category": specific_category,
            "spending": spending,
            "cap": cap,
            "percentage": percentage,
            "remaining": remaining
        }
        return [TextContent(type="text", text=json.dumps(result))]

    # Return all categories (status format)
    categories = []
    for expense_type in ExpenseType:
        cap = all_caps.get(expense_type.name, 0)
        spending = category_spending.get(expense_type.name, 0)

        if cap > 0:
            percentage = (spending / cap) * 100
            remaining = cap - spending

            categories.append({
                "category": expense_type.name,
                "spending": spending,
                "cap": cap,
                "percentage": percentage,
                "remaining": remaining
            })

    # Calculate total
    total_spending = sum(category_spending.values())
    total_percentage = (total_spending / total_cap * 100) if total_cap else 0
    total_remaining = total_cap - total_spending if total_cap else 0

    result = {
        "categories": categories,
        "total": {
            "spending": total_spending,
            "cap": total_cap,
            "percentage": total_percentage,
            "remaining": total_remaining
        }
    }

    return [TextContent(type="text", text=json.dumps(result))]


async def _compare_periods(arguments: dict) -> list[TextContent]:
    """
    Compare spending between two periods.

    Args:
        arguments: {
            "period1_start": {day, month, year},
            "period1_end": {day, month, year},
            "period2_start": {day, month, year},
            "period2_end": {day, month, year},
            "category": str (optional)
        }

    Returns:
        TextContent with comparison data
    """
    import json

    # Parse dates for period 1
    p1_start = Date(
        day=arguments["period1_start"]["day"],
        month=arguments["period1_start"]["month"],
        year=arguments["period1_start"]["year"]
    )
    p1_end = Date(
        day=arguments["period1_end"]["day"],
        month=arguments["period1_end"]["month"],
        year=arguments["period1_end"]["year"]
    )

    # Parse dates for period 2
    p2_start = Date(
        day=arguments["period2_start"]["day"],
        month=arguments["period2_start"]["month"],
        year=arguments["period2_start"]["year"]
    )
    p2_end = Date(
        day=arguments["period2_end"]["day"],
        month=arguments["period2_end"]["month"],
        year=arguments["period2_end"]["year"]
    )

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get category filter
    category = None
    if "category" in arguments and arguments["category"]:
        category = ExpenseType[arguments["category"]]

    # Get expenses for both periods
    p1_expenses = firebase.get_expenses_in_date_range(p1_start, p1_end, category)
    p2_expenses = firebase.get_expenses_in_date_range(p2_start, p2_end, category)

    # Calculate totals
    p1_total = sum(exp.get("amount", 0) for exp in p1_expenses)
    p2_total = sum(exp.get("amount", 0) for exp in p2_expenses)

    # Calculate difference
    difference = p2_total - p1_total
    percentage_change = ((p2_total - p1_total) / p1_total * 100) if p1_total > 0 else 0

    result = {
        "period1": {
            "start": arguments["period1_start"],
            "end": arguments["period1_end"],
            "total": p1_total,
            "count": len(p1_expenses)
        },
        "period2": {
            "start": arguments["period2_start"],
            "end": arguments["period2_end"],
            "total": p2_total,
            "count": len(p2_expenses)
        },
        "comparison": {
            "difference": difference,
            "percentage_change": percentage_change
        }
    }

    if category:
        result["category"] = category.name

    return [TextContent(type="text", text=json.dumps(result))]


async def _get_largest_expenses(arguments: dict) -> list[TextContent]:
    """
    Get top 3 largest expenses.

    Args:
        arguments: {
            "start_date": {day, month, year},
            "end_date": {day, month, year},
            "category": str (optional)
        }

    Returns:
        TextContent with top 3 expenses
    """
    import json

    # Parse dates
    start_date_dict = arguments["start_date"]
    end_date_dict = arguments["end_date"]
    start_date = Date(
        day=start_date_dict["day"],
        month=start_date_dict["month"],
        year=start_date_dict["year"]
    )
    end_date = Date(
        day=end_date_dict["day"],
        month=end_date_dict["month"],
        year=end_date_dict["year"]
    )

    # Get user-scoped Firebase client
    firebase = get_user_firebase(arguments)

    # Get category filter
    category = None
    if "category" in arguments and arguments["category"]:
        category = ExpenseType[arguments["category"]]

    # Get all expenses
    expenses = firebase.get_expenses_in_date_range(start_date, end_date, category)

    # Sort by amount (highest first) and take top 3
    expenses.sort(key=lambda x: x.get("amount", 0), reverse=True)
    top_3 = expenses[:3]

    result = {
        "largest_expenses": [
            {
                "name": exp.get("expense_name"),
                "amount": exp.get("amount"),
                "date": exp.get("date"),
                "category": exp.get("category")
            }
            for exp in top_3
        ],
        "start_date": start_date_dict,
        "end_date": end_date_dict
    }

    if category:
        result["category"] = category.name

    return [TextContent(type="text", text=json.dumps(result))]


async def main():
    """
    Main entry point for the MCP server.
    Runs the server with stdio transport.
    """
    # Run the server using stdio (reads from stdin, writes to stdout)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="expense-tracker-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
