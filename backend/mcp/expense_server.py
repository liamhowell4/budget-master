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
from backend.output_schemas import Expense, ExpenseType, Date


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
