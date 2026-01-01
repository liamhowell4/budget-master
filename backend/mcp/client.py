"""
MCP Client Wrapper for FastAPI - Handles expense parsing via Claude + MCP.

This module wraps the MCP client for use in FastAPI, providing:
- Connection management (startup/shutdown)
- Expense message processing with Claude API
- System prompt integration
- Tool orchestration
"""

import os
import json
import base64
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import date
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic

from backend.system_prompts import get_expense_parsing_system_prompt

# Claude model constant
ANTHROPIC_MODEL = "claude-sonnet-4-5"


class MCPClient:
    """
    Core MCP client for connecting to MCP servers via stdio.

    Handles:
    - Server connection management
    - Tool discovery
    - Claude API integration with MCP tools
    """

    def __init__(self):
        """Initialize MCP client."""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )

    async def connect_to_server(self, server_script_path: str):
        """
        Connect to an MCP server via stdio.

        Args:
            server_script_path: Path to the server script (.py file)
        """
        is_python = server_script_path.endswith('.py')
        if not is_python:
            raise ValueError("Server script must be a .py file")

        path = Path(server_script_path).resolve()

        # Pass environment variables to subprocess (important for Cloud Run secrets)
        env = os.environ.copy()

        server_params = StdioServerParameters(
            command="python",
            args=[str(path)],
            env=env,
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


class ExpenseMCPClient:
    """
    FastAPI wrapper for MCP client.

    Manages MCP server connection and provides expense processing methods.
    """

    def __init__(self):
        """Initialize the expense MCP client."""
        self.client: Optional[MCPClient] = None
        self.server_path = os.path.join(
            os.path.dirname(__file__),
            'expense_server.py'
        )

    async def startup(self):
        """
        Start the MCP client and connect to expense server.

        This spawns the expense_server.py as a subprocess and establishes
        stdio connection for tool calls.

        Raises:
            Exception: If connection fails
        """
        print("🔄 Starting MCP client...")
        self.client = MCPClient()

        # Connect to expense server
        await self.client.connect_to_server(self.server_path)
        print("✅ MCP client connected to expense server")

    async def process_expense_message(
        self,
        text: str,
        image_base64: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an expense message using Claude + MCP tools.

        This method:
        1. Gets recent expense context from conversation cache
        2. Builds a message with text and/or image
        3. Calls Claude API with system prompt, context, and MCP tools
        4. Orchestrates tool calls (save_expense, update_expense, delete_expense, etc.)
        5. Updates conversation cache after saving/updating
        6. Returns structured response

        Args:
            text: Text description of expense (e.g., "Starbucks $5", "Actually make that $6")
            image_base64: Optional base64-encoded image (receipt photo)
            user_id: Phone number or session ID for conversation tracking

        Returns:
            {
                "success": True,
                "expense_id": "abc123",
                "expense_name": "Starbucks coffee",
                "amount": 5.0,
                "category": "COFFEE",
                "budget_warning": "⚠️ 90% of COFFEE budget used ($10 left)",
                "message": "✅ Saved $5 Starbucks coffee (COFFEE)\n⚠️ 90% of COFFEE budget used ($10 left)"
            }

        Raises:
            Exception: If processing fails
        """
        if not self.client:
            raise RuntimeError("MCP client not initialized. Call startup() first.")

        # Get conversation cache
        from .conversation_cache import get_conversation_cache
        cache = get_conversation_cache()

        # Get recent expenses for context (if user_id provided)
        recent_expenses = []
        if user_id:
            recent_expenses = cache.get_recent_expenses(user_id, limit=5)

        # Build message content
        message_content = []

        # Add recent expense context if available
        if recent_expenses:
            context_text = "**Recent Expenses (for context):**\n"
            for i, exp in enumerate(recent_expenses, 1):
                date_obj = exp.get("date", {})
                date_str = f"{date_obj.get('month')}/{date_obj.get('day')}/{date_obj.get('year')}" if date_obj else "Unknown"
                context_text += f"{i}. ${exp['amount']:.2f} {exp['expense_name']} ({exp['category']}) - {date_str} [ID: {exp['expense_id']}]\n"

            message_content.append({
                "type": "text",
                "text": context_text.strip()
            })

        # Add text
        if text:
            message_content.append({
                "type": "text",
                "text": text
            })

        # Add image if provided
        if image_base64:
            # Determine media type from base64 prefix
            media_type = "image/jpeg"  # Default
            if image_base64.startswith("data:"):
                # Extract media type from data URL
                media_type = image_base64.split(";")[0].split(":")[1]
                # Remove data URL prefix to get just the base64 data
                image_base64 = image_base64.split(",")[1]

            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_base64
                }
            })

        # Get system prompt
        system_prompt = get_expense_parsing_system_prompt()

        # Get available tools from MCP server
        response = await self.client.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Build messages
        messages = [{"role": "user", "content": message_content}]

        # Call Claude API with tools
        response = self.client.anthropic.messages.create(
            model=ANTHROPIC_MODEL,
            system=system_prompt,
            max_tokens=2000,
            messages=messages,
            tools=available_tools
        )

        # Track expense data from tool results
        expense_data = {
            "success": False,
            "expense_id": None,
            "expense_name": None,
            "amount": None,
            "category": None,
            "budget_warning": "",
            "message": ""
        }

        final_text = []

        # Process response and handle tool calls in a loop
        while response.stop_reason == "tool_use":
            # Collect all tool uses and text from this response
            assistant_content = []
            tool_results = []

            for content in response.content:
                if content.type == 'text':
                    final_text.append(content.text)
                    assistant_content.append({"type": "text", "text": content.text})
                elif content.type == 'tool_use':
                    tool_name = content.name
                    tool_args = content.input
                    tool_use_id = content.id

                    print(f"🔧 Calling tool: {tool_name}")

                    # Execute tool call via MCP
                    result = await self.client.session.call_tool(tool_name, tool_args)

                    # Parse tool result
                    if hasattr(result, 'content') and result.content:
                        if isinstance(result.content, list):
                            result_text = "\n".join(
                                block.text if hasattr(block, 'text') else str(block)
                                for block in result.content
                            )
                        else:
                            result_text = str(result.content)
                    else:
                        result_text = str(result)

                    # Extract data from tool results
                    try:
                        result_data = json.loads(result_text)

                        if tool_name == "save_expense":
                            expense_data["success"] = result_data.get("success", False)
                            expense_data["expense_id"] = result_data.get("expense_id")
                            expense_data["expense_name"] = result_data.get("expense_name")
                            expense_data["amount"] = result_data.get("amount")
                            expense_data["category"] = result_data.get("category")

                            # Update conversation cache with new expense
                            if user_id and expense_data["expense_id"]:
                                cache.update_last_expense(
                                    user_id=user_id,
                                    expense_id=expense_data["expense_id"],
                                    expense_name=expense_data["expense_name"],
                                    amount=expense_data["amount"],
                                    category=expense_data["category"]
                                )

                        elif tool_name == "update_expense":
                            expense_data["success"] = result_data.get("success", False)
                            expense_data["expense_id"] = result_data.get("expense_id")
                            expense_data["expense_name"] = result_data.get("expense_name")
                            expense_data["amount"] = result_data.get("amount")
                            expense_data["category"] = result_data.get("category")

                            # Update cache with updated expense details
                            if user_id and expense_data["expense_id"]:
                                cache.update_last_expense(
                                    user_id=user_id,
                                    expense_id=expense_data["expense_id"],
                                    expense_name=expense_data["expense_name"],
                                    amount=expense_data["amount"],
                                    category=expense_data["category"]
                                )

                        elif tool_name == "delete_expense":
                            expense_data["success"] = result_data.get("success", False)
                            # Note: For deletes, we don't update cache since expense is gone

                        elif tool_name == "get_budget_status":
                            expense_data["budget_warning"] = result_data.get("budget_warning", "")

                    except json.JSONDecodeError:
                        print(f"⚠️ Could not parse tool result as JSON: {result_text}")

                    # Add tool_use to assistant content
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_args
                    })

                    # Collect tool result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_text
                    })

            # Add assistant message with tool uses
            messages.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Add user message with tool results
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Get next response from Claude - WITH TOOLS so it can call more!
            response = self.client.anthropic.messages.create(
                model=ANTHROPIC_MODEL,
                system=system_prompt,
                max_tokens=2000,
                messages=messages,
                tools=available_tools
            )

        # Process final response (no more tool calls)
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)

        # Build final message
        expense_data["message"] = "\n".join(final_text)

        return expense_data

    async def cleanup(self):
        """
        Clean up MCP client resources.

        This closes the stdio connection and terminates the server subprocess.
        """
        if self.client:
            print("🔄 Shutting down MCP client...")
            await self.client.cleanup()
            print("✅ MCP client shut down")
