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


# Initialize Firebase and Budget Manager
firebase_client = FirebaseClient()
budget_manager = BudgetManager(firebase_client)

# Create MCP server
server = Server("expense-tracker-mcp")


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
                    "name": {
                        "type": "string",
                        "description": "Descriptive name for the expense (e.g., 'Starbucks coffee', 'Chipotle lunch')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Dollar amount of the expense (e.g., 5.50, 15.00)"
                    },
                    "date": {
                        "type": "object",
                        "description": "Date of the expense",
                        "properties": {
                            "day": {"type": "integer", "minimum": 1, "maximum": 31},
                            "month": {"type": "integer", "minimum": 1, "maximum": 12},
                            "year": {"type": "integer", "minimum": 2000}
                        },
                        "required": ["day", "month", "year"]
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category key (e.g., 'FOOD_OUT', 'COFFEE', 'GROCERIES'). Use get_categories to see all valid options.",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["name", "amount", "date", "category"]
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
                "required": ["category", "amount", "year", "month"]
            }
        ),
        Tool(
            name="get_categories",
            description=(
                "Get all valid expense categories with their descriptions. "
                "Use this to understand which category to assign to an expense."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
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
                        "description": "New amount (optional)"
                    },
                    "date": {
                        "type": "object",
                        "description": "New date (optional)",
                        "properties": {
                            "day": {"type": "integer", "minimum": 1, "maximum": 31},
                            "month": {"type": "integer", "minimum": 1, "maximum": 12},
                            "year": {"type": "integer", "minimum": 2000}
                        },
                        "required": ["day", "month", "year"]
                    },
                    "category": {
                        "type": "string",
                        "description": "New category (optional)",
                        "enum": [e.name for e in ExpenseType]
                    }
                },
                "required": ["expense_id"]
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
                    "expense_id": {
                        "type": "string",
                        "description": "The Firebase document ID of the expense to delete"
                    }
                },
                "required": ["expense_id"]
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
                "required": []
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
                "required": ["query"]
            }
        ),
        Tool(
            name="create_recurring_expense",
            description=(
                "Create a recurring expense template for subscriptions, rent, bills, etc. "
                "The system will automatically create pending expenses on the specified schedule. "
                "Supports monthly (on specific day), weekly (on specific weekday), and biweekly frequencies."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the recurring expense (e.g., 'Libro.fm subscription', 'Rent', 'Netflix')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount of the recurring expense"
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category",
                        "enum": [e.name for e in ExpenseType]
                    },
                    "frequency": {
                        "type": "string",
                        "description": "How often the expense recurs",
                        "enum": ["monthly", "weekly", "biweekly"]
                    },
                    "day_of_month": {
                        "type": "integer",
                        "description": "Day of month (1-31) for monthly recurring expenses. Required if frequency is 'monthly'.",
                        "minimum": 1,
                        "maximum": 31
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
                "required": ["name", "amount", "category", "frequency"]
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
                    "active_only": {
                        "type": "boolean",
                        "description": "Only show active recurring expenses (default true)",
                        "default": True
                    }
                },
                "required": []
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
                    "template_id": {
                        "type": "string",
                        "description": "The Firebase document ID of the recurring expense template to delete"
                    }
                },
                "required": ["template_id"]
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

    # Parse category
    try:
        category = ExpenseType[category_str]
    except KeyError:
        return [TextContent(
            type="text",
            text=f"Error: Invalid category '{category_str}'. Use get_categories to see valid options."
        )]

    # Create Expense object
    expense = Expense(
        expense_name=expense_name,
        amount=amount,
        date=expense_date,
        category=category
    )

    # Save to Firebase
    expense_id = firebase_client.save_expense(expense, input_type="mcp")

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
    category_str = arguments["category"]
    amount = float(arguments["amount"])
    year = int(arguments["year"])
    month = int(arguments["month"])

    # Parse category
    try:
        category = ExpenseType[category_str]
    except KeyError:
        return [TextContent(
            type="text",
            text=f"Error: Invalid category '{category_str}'"
        )]

    # Get budget warning
    warning = budget_manager.get_budget_warning(
        category=category,
        amount=amount,
        year=year,
        month=month
    )

    # Return warning (empty string if no warnings)
    result = {
        "budget_warning": warning if warning else ""
    }

    import json
    return [TextContent(type="text", text=json.dumps(result))]


async def _get_categories(arguments: dict) -> list[TextContent]:
    """
    Get all valid expense categories.

    Args:
        arguments: {} (no arguments needed)

    Returns:
        TextContent with category list
    """
    categories = []
    for expense_type in ExpenseType:
        categories.append({
            "key": expense_type.name,
            "description": expense_type.value
        })

    import json
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

    # Convert category string to ExpenseType if provided
    category_obj = None
    if category_str:
        try:
            category_obj = ExpenseType[category_str]
        except KeyError:
            return [TextContent(
                type="text",
                text=f"Error: Invalid category '{category_str}'"
            )]

    # Update expense
    success = firebase_client.update_expense(
        expense_id=expense_id,
        expense_name=expense_name,
        amount=amount,
        date=date_obj,
        category=category_obj
    )

    if not success:
        return [TextContent(
            type="text",
            text=f"Error: Expense {expense_id} not found"
        )]

    # Get updated expense to return details
    updated_expense = firebase_client.get_expense_by_id(expense_id)

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

    # Get expense details before deleting (for confirmation message)
    expense = firebase_client.get_expense_by_id(expense_id)

    if not expense:
        return [TextContent(
            type="text",
            text=f"Error: Expense {expense_id} not found"
        )]

    # Delete expense
    success = firebase_client.delete_expense(expense_id)

    if not success:
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
    expenses = firebase_client.get_recent_expenses_from_db(
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
    expenses = firebase_client.search_expenses_in_db(
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
            "frequency": str ("monthly", "weekly", "biweekly"),
            "day_of_month": int (optional, for monthly),
            "day_of_week": int (optional, for weekly/biweekly),
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
    last_of_month = arguments.get("last_of_month", False)

    # Convert category string to ExpenseType enum
    try:
        category = ExpenseType[category_str]
    except KeyError:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Invalid category: {category_str}"
        }))]

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
        last_of_month=last_of_month,
        last_reminded=None,  # Will be set when first pending expense is created
        last_user_action=today_date,  # Set to today to avoid immediate retroactive pending
        active=True
    )

    # Save to Firebase
    template_id = firebase_client.save_recurring_expense(recurring)

    result = {
        "success": True,
        "template_id": template_id,
        "expense_name": name,
        "amount": amount,
        "category": category_str,
        "frequency": frequency_str,
        "message": f"✅ Created recurring expense: {name} (${amount:.2f} {frequency_str})"
    }

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

    # Get recurring expenses from Firebase
    recurring_list = firebase_client.get_all_recurring_expenses(active_only=active_only)

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

    # Get the expense first to return details
    recurring = firebase_client.get_recurring_expense(template_id)

    if not recurring:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Recurring expense {template_id} not found"
        }))]

    # Delete the recurring expense
    firebase_client.delete_recurring_expense(template_id)

    result = {
        "success": True,
        "template_id": template_id,
        "expense_name": recurring.expense_name,
        "amount": recurring.amount,
        "message": f"✅ Deleted recurring expense: {recurring.expense_name} (${recurring.amount:.2f})"
    }

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
