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
import logging
import base64
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import date
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.system_prompts import get_expense_parsing_system_prompt
from backend.model_client import UnifiedModelClient, SUPPORTED_MODELS, DEFAULT_MODEL


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
        logger.info("Connected to server with tools: %s", [tool.name for tool in tools])

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

    def _patch_category_enum(self, input_schema: dict, category_ids: list) -> dict:
        """
        Recursively patch category enum values in a tool's input schema.

        This allows dynamic categories to be used in MCP tools instead of
        the hardcoded ExpenseType enum.

        Args:
            input_schema: The tool's input schema (JSON Schema format)
            category_ids: List of user's category IDs

        Returns:
            Patched schema with updated category enum
        """
        import copy

        schema = copy.deepcopy(input_schema)

        def patch_properties(properties: dict):
            for prop_name, prop_schema in properties.items():
                # Check if this property is a category field with enum
                if prop_name == "category" and "enum" in prop_schema:
                    prop_schema["enum"] = category_ids

        # Patch top-level properties
        if "properties" in schema:
            patch_properties(schema["properties"])

        return schema

    async def startup(self):
        """
        Start the MCP client and connect to expense server.

        This spawns the expense_server.py as a subprocess and establishes
        stdio connection for tool calls.

        Raises:
            Exception: If connection fails
        """
        logger.info("Starting MCP client...")
        self.client = MCPClient()

        # Connect to expense server
        await self.client.connect_to_server(self.server_path)
        logger.info("MCP client connected to expense server")

    async def process_expense_message(
        self,
        text: str,
        image_base64: Optional[str] = None,
        auth_token: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """
        Process an expense message using Claude + MCP tools.

        This method:
        1. Gets recent expense context from Firestore conversation
        2. Builds a message with text and/or image
        3. Calls Claude API with system prompt, context, and MCP tools
        4. Orchestrates tool calls (save_expense, update_expense, delete_expense, etc.)
        5. Updates Firestore conversation after saving/updating
        6. Returns structured response

        Args:
            text: Text description of expense (e.g., "Starbucks $5", "Actually make that $6")
            image_base64: Optional base64-encoded image (receipt photo)
            auth_token: Firebase Auth ID token for MCP tool authentication
            user_id: User ID for Firestore conversation (extracted from auth_token at API layer)
            conversation_id: Optional conversation ID for context continuity

        Returns:
            {
                "success": True,
                "expense_id": "abc123",
                "expense_name": "Starbucks coffee",
                "amount": 5.0,
                "category": "COFFEE",
                "budget_warning": "⚠️ 90% of COFFEE budget used ($10 left)",
                "message": "✅ Saved $5 Starbucks coffee (COFFEE)\n⚠️ 90% of COFFEE budget used ($10 left)",
                "conversation_id": "conv123"
            }

        Raises:
            Exception: If processing fails
        """
        if not self.client:
            raise RuntimeError("MCP client not initialized. Call startup() first.")

        # Get or create conversation in Firestore
        from backend.firebase_client import FirebaseClient
        from datetime import datetime, timedelta
        import pytz

        user_firebase = None
        conversation_messages = []
        if user_id:
            user_firebase = FirebaseClient.for_user(user_id)

            # Check if existing conversation is stale (>1 hour idle)
            if conversation_id:
                existing_conv = user_firebase.get_conversation(conversation_id)
                if existing_conv:
                    last_activity = existing_conv.get("last_activity")
                    if last_activity:
                        # Check if more than 1 hour has passed
                        user_timezone = os.getenv("USER_TIMEZONE", "America/Chicago")
                        tz = pytz.timezone(user_timezone)
                        now = datetime.now(tz)

                        # Handle Firestore timestamp
                        if hasattr(last_activity, 'timestamp'):
                            last_activity = last_activity.timestamp()
                            last_activity = datetime.fromtimestamp(last_activity, tz)
                        elif isinstance(last_activity, datetime):
                            if last_activity.tzinfo is None:
                                last_activity = tz.localize(last_activity)

                        if now - last_activity > timedelta(hours=1):
                            logger.info("Conversation %s is stale (>1 hour), creating new one", conversation_id)
                            conversation_id = None  # Will create new one below
                        else:
                            # Get existing messages for context
                            conversation_messages = existing_conv.get("messages", [])
                else:
                    conversation_id = None  # Conversation not found, create new

            # Create new conversation if none provided or stale
            if not conversation_id:
                conversation_id = user_firebase.create_conversation()

        # Get recent expenses for context from Firestore conversation
        recent_expenses = []
        if user_firebase and conversation_id:
            recent_expenses = user_firebase.get_conversation_recent_expenses(conversation_id, limit=5)

        # Get user's custom categories for dynamic prompts and tool schemas
        user_categories = None
        if user_firebase:
            # Ensure categories are set up (silent migration)
            if not user_firebase.has_categories_setup():
                user_firebase.migrate_from_budget_caps()
            user_categories = user_firebase.get_user_categories()

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

        # Get system prompt with user's categories
        system_prompt = get_expense_parsing_system_prompt(user_categories)

        # Get available tools from MCP server
        response = await self.client.session.list_tools()
        available_tools = []

        # Build category enum from user's categories (or fallback to ExpenseType)
        if user_categories:
            category_enum = [cat.get("category_id") for cat in user_categories]
        else:
            from backend.output_schemas import ExpenseType
            category_enum = [e.name for e in ExpenseType]

        # Patch tool schemas to use user's dynamic categories
        for tool in response.tools:
            tool_schema = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": self._patch_category_enum(tool.inputSchema, category_enum)
            }
            available_tools.append(tool_schema)

        # Build messages with conversation history
        messages = []

        # Add previous conversation messages for context (if any)
        if conversation_messages:
            for msg in conversation_messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # Add current user message
        messages.append({"role": "user", "content": message_content})

        # Call model API with tools
        model_client = UnifiedModelClient(model)
        provider = SUPPORTED_MODELS[model]["provider"]

        response = model_client.create(
            system=system_prompt,
            messages=messages,
            tools=available_tools,
        )

        # Log token usage for initial call
        if user_firebase and user_id:
            user_firebase.log_token_usage(
                user_id, model, provider,
                response.input_tokens, response.output_tokens, "process_expense"
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

            if response.content:
                final_text.append(response.content)
                assistant_content.append({"type": "text", "text": response.content})

            for tc in response.tool_calls:
                tool_name = tc.name
                tool_args = tc.arguments
                tool_use_id = tc.id

                logger.info("Calling tool: %s", tool_name)

                # Inject auth_token into tool arguments for multi-user support
                # The model doesn't know the auth token, so we inject it here.
                # MCP server will verify the token with Firebase Auth.
                if auth_token:
                    tool_args = {**tool_args, "auth_token": auth_token}

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

                        # Update Firestore conversation with new expense
                        if user_firebase and conversation_id and expense_data["expense_id"]:
                            user_firebase.update_conversation_recent_expenses(
                                conversation_id=conversation_id,
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

                        # Update Firestore conversation with updated expense details
                        if user_firebase and conversation_id and expense_data["expense_id"]:
                            user_firebase.update_conversation_recent_expenses(
                                conversation_id=conversation_id,
                                expense_id=expense_data["expense_id"],
                                expense_name=expense_data["expense_name"],
                                amount=expense_data["amount"],
                                category=expense_data["category"]
                            )

                    elif tool_name == "delete_expense":
                        expense_data["success"] = result_data.get("success", False)
                        # Note: For deletes, we don't update conversation since expense is gone

                    elif tool_name == "get_budget_status":
                        expense_data["budget_warning"] = result_data.get("budget_warning", "")

                except json.JSONDecodeError:
                    logger.warning("Could not parse tool result as JSON: %s", result_text)

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

            # Get next response from model - WITH TOOLS so it can call more!
            response = model_client.create(
                system=system_prompt,
                messages=messages,
                tools=available_tools,
            )

            # Log token usage for each subsequent call
            if user_firebase and user_id:
                user_firebase.log_token_usage(
                    user_id, model, provider,
                    response.input_tokens, response.output_tokens, "process_expense"
                )

        # Process final response (no more tool calls)
        if response.content:
            final_text.append(response.content)

        # Build final message
        expense_data["message"] = "\n".join(final_text)

        # Store messages in Firestore conversation
        if user_firebase and conversation_id:
            # Store user message
            user_message = text or "[Image/Audio input]"
            user_firebase.add_message_to_conversation(conversation_id, "user", user_message)

            # Store assistant response
            if expense_data["message"]:
                user_firebase.add_message_to_conversation(conversation_id, "assistant", expense_data["message"])

            # Generate summary from the interaction
            summary_parts = []
            if expense_data.get("expense_name"):
                action = "Added" if expense_data.get("success") else "Attempted"
                summary_parts.append(f"{action} ${expense_data.get('amount', 0):.2f} {expense_data['expense_name']}")
            if not summary_parts:
                summary_parts.append(text[:50] if text else "Expense interaction")
            user_firebase.update_conversation_summary(conversation_id, ", ".join(summary_parts))

        # Include conversation_id in response
        expense_data["conversation_id"] = conversation_id

        return expense_data

    async def cleanup(self):
        """
        Clean up MCP client resources.

        This closes the stdio connection and terminates the server subprocess.
        """
        if self.client:
            logger.info("Shutting down MCP client...")
            await self.client.cleanup()
            logger.info("MCP client shut down")
