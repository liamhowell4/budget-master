"""
Chat stream helpers — decomposed from api.py chat_stream() endpoint.

Helpers:
  get_or_create_conversation()  — resolve or create conversation
  build_message_context()       — assemble Claude message list
  run_claude_tool_loop()        — async generator yielding SSE events
  save_conversation_history()   — persist messages to Firestore
"""

import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator

import anthropic
from anthropic import Anthropic

from .firebase_client import FirebaseClient

logger = logging.getLogger(__name__)


@dataclass
class ToolLoopResult:
    """Accumulates output from run_claude_tool_loop."""

    final_response_text: list[str] = field(default_factory=list)
    all_tool_calls: list[dict] = field(default_factory=list)
    had_error: bool = False


def get_or_create_conversation(
    user_firebase: FirebaseClient,
    conversation_id: Optional[str],
    user_timezone,
    inactivity_threshold_hours: int = 12,
) -> tuple[str, list[dict]]:
    """
    Resolve an existing conversation or create a new one.

    If conversation_id is provided, checks staleness (> inactivity_threshold_hours).
    Stale or missing conversations get a fresh ID.

    Returns:
        (conversation_id, conversation_messages) where conversation_messages
        is the existing history (empty list for new conversations).
    """
    conversation_messages: list[dict] = []

    if conversation_id:
        existing_conv = user_firebase.get_conversation(conversation_id)
        if existing_conv:
            last_activity = existing_conv.get("last_activity")
            if last_activity:
                now = datetime.now(user_timezone)

                # Handle Firestore timestamp
                if hasattr(last_activity, 'timestamp'):
                    last_activity = datetime.fromtimestamp(
                        last_activity.timestamp(), user_timezone
                    )
                elif isinstance(last_activity, datetime):
                    if last_activity.tzinfo is None:
                        last_activity = user_timezone.localize(last_activity)

                if now - last_activity > timedelta(hours=inactivity_threshold_hours):
                    logger.info(
                        "Conversation %s is stale (>%dh), creating new one",
                        conversation_id, inactivity_threshold_hours,
                    )
                    conversation_id = None
                else:
                    # Get existing messages for context
                    conversation_messages = existing_conv.get("messages", [])
        else:
            conversation_id = None  # Conversation not found

    # Create new conversation if needed
    if not conversation_id:
        conversation_id = user_firebase.create_conversation()

    return conversation_id, conversation_messages


def build_message_context(
    conversation_messages: list[dict],
    current_message: str,
) -> list[dict]:
    """
    Build the messages list for the Claude API call.

    Prepends conversation history, appends the current user message.
    """
    messages = []

    for msg in conversation_messages:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })

    messages.append({
        "role": "user",
        "content": current_message,
    })

    return messages


async def run_claude_tool_loop(
    client,
    messages: list[dict],
    system_prompt: str,
    anthropic_api_key: str,
    current_user_token: str,
    result: ToolLoopResult,
) -> AsyncGenerator[str, None]:
    """
    Run the Claude API tool-use loop, yielding SSE-formatted strings.

    Calls client.session.list_tools() and client.session.call_tool()
    for MCP interactions. Mutates *result* to accumulate response text
    and tool calls.

    On Claude API errors: sets result.had_error = True, yields an error
    event, and returns. The caller is responsible for yielding [DONE].
    """
    # Get available tools from MCP server
    response = await client.session.list_tools()
    available_tools = [{
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.inputSchema,
    } for tool in response.tools]

    # Call Claude API with tools
    anthropic_client = Anthropic(api_key=anthropic_api_key)
    try:
        api_response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            system=system_prompt,
            max_tokens=2000,
            messages=messages,
            tools=available_tools,
        )
    except (anthropic.APIError, anthropic.APITimeoutError) as api_err:
        logger.error("Claude API error: %s", api_err)
        result.had_error = True
        error_event = {"type": "error", "content": f"AI service error: {api_err}"}
        yield f"data: {json.dumps(error_event)}\n\n"
        return

    # Process response and handle tool calls in a loop
    while api_response.stop_reason == "tool_use":
        assistant_content = []
        tool_results = []

        for content in api_response.content:
            if content.type == 'text':
                assistant_content.append({
                    "type": "text",
                    "text": content.text,
                })
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input
                tool_use_id = content.id

                # Inject auth_token for MCP tool authentication (defense in depth)
                if tool_name != "get_categories":
                    tool_args = {**tool_args, "auth_token": current_user_token}

                # Emit tool_start event (without auth token for security)
                tool_start_event = {
                    "type": "tool_start",
                    "id": tool_use_id,
                    "name": tool_name,
                    "args": {k: v for k, v in tool_args.items() if k != "auth_token"},
                }
                yield f"data: {json.dumps(tool_start_event)}\n\n"

                # Execute tool call via MCP
                try:
                    tool_result = await client.session.call_tool(tool_name, tool_args)
                except Exception as tool_err:
                    logger.error("MCP call_tool failed for %s: %s", tool_name, tool_err)
                    result_text = json.dumps({"error": f"Tool execution failed: {tool_err}"})
                else:
                    # Parse tool result
                    if hasattr(tool_result, 'content') and tool_result.content:
                        if isinstance(tool_result.content, list):
                            result_text = "\n".join(
                                block.text if hasattr(block, 'text') else str(block)
                                for block in tool_result.content
                            )
                        else:
                            result_text = str(tool_result.content)
                    else:
                        result_text = str(tool_result)

                # Emit tool_end event with result
                try:
                    parsed_result = json.loads(result_text)
                except (json.JSONDecodeError, TypeError):
                    parsed_result = result_text

                tool_end_event = {
                    "type": "tool_end",
                    "id": tool_use_id,
                    "name": tool_name,
                    "result": parsed_result,
                }
                yield f"data: {json.dumps(tool_end_event)}\n\n"

                # Collect tool call for persistence
                result.all_tool_calls.append({
                    "id": tool_use_id,
                    "name": tool_name,
                    "args": {k: v for k, v in tool_args.items() if k != "auth_token"},
                    "result": parsed_result,
                })

                # Add tool_use to assistant content
                assistant_content.append({
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_name,
                    "input": tool_args,
                })

                # Collect tool result
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_text,
                })

        # Add assistant message with tool uses
        messages.append({
            "role": "assistant",
            "content": assistant_content,
        })

        # Add user message with tool results
        messages.append({
            "role": "user",
            "content": tool_results,
        })

        # Get next response from Claude
        try:
            api_response = anthropic_client.messages.create(
                model="claude-sonnet-4-5",
                system=system_prompt,
                max_tokens=2000,
                messages=messages,
                tools=available_tools,
            )
        except (anthropic.APIError, anthropic.APITimeoutError) as api_err:
            logger.error("Claude API error during tool loop: %s", api_err)
            result.had_error = True
            error_event = {"type": "error", "content": f"AI service error: {api_err}"}
            yield f"data: {json.dumps(error_event)}\n\n"
            return

    # Process final response (no more tool calls)
    for content in api_response.content:
        if content.type == 'text':
            text = content.text
            result.final_response_text.append(text)

            if len(text) > 0:
                text_event = {
                    "type": "text",
                    "content": text,
                }
                yield f"data: {json.dumps(text_event)}\n\n"


def save_conversation_history(
    user_firebase: FirebaseClient,
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    tool_calls: list[dict],
    conversation_messages: list[dict],
) -> None:
    """
    Persist user and assistant messages to the Firestore conversation.

    Sets the conversation summary from the first user message.
    """
    user_firebase.add_message_to_conversation(
        conversation_id, "user", user_message
    )

    if assistant_response:
        user_firebase.add_message_to_conversation(
            conversation_id, "assistant", assistant_response,
            tool_calls=tool_calls if tool_calls else None,
        )

    # Update conversation summary from first user message
    if len(conversation_messages) == 0:
        summary = user_message[:50]
        if len(user_message) > 50:
            summary += "..."
        user_firebase.update_conversation_summary(conversation_id, summary)
