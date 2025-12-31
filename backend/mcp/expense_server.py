#!/usr/bin/env python3
"""
MCP Expense Server - Exposes expense tracking tools via Model Context Protocol.

This server runs as a subprocess and communicates via stdio (stdin/stdout).
It provides three tools for Claude to use:
1. save_expense - Save a parsed expense to Firebase
2. get_budget_status - Check budget status and get warnings
3. get_categories - List all valid expense categories

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
