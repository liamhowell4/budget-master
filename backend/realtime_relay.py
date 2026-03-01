"""
OpenAI Realtime API relay for the Watch conversational voice assistant.

Architecture:
    Watch → PCM16 audio chunks → /ws/realtime → OpenAI wss://api.openai.com/v1/realtime
    OpenAI calls MCP tools → relay executes → OpenAI speaks + types response
    Watch ← response audio/text ← relay

Watch ↔ Backend protocol (JSON over WebSocket):
    Watch → Backend:  {"type": "audio_chunk", "data": "<base64 pcm16>"}
                      {"type": "audio_done"}
                      {"type": "cancel"}
    Backend → Watch:  {"type": "input_transcript",     "text": "..."}
                      {"type": "response_text_delta",  "text": "..."}
                      {"type": "response_audio_delta", "data": "<base64 pcm16>"}
                      {"type": "response_done",        "expense_saved": {...} | null}
                      {"type": "error",                "message": "..."}
"""

import os
import json
import asyncio
import logging
import copy
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from backend.system_prompts import get_expense_parsing_system_prompt

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
VOICE_PREAMBLE = (
    "For voice responses, keep answers under 3 sentences. "
    "Do not list items; speak naturally."
)


# ---------------------------------------------------------------------------
# Tool Schema Helpers
# ---------------------------------------------------------------------------

def _patch_category_enum(input_schema: dict, category_ids: list) -> dict:
    schema = copy.deepcopy(input_schema)
    props = schema.get("properties", {})
    for prop_name, prop_schema in props.items():
        if prop_name == "category" and "enum" in prop_schema:
            prop_schema["enum"] = category_ids
    return schema


async def _build_realtime_tools(mcp_client, user_categories: Optional[list]) -> list:
    """
    Fetch MCP tools and convert to OpenAI Realtime function format.

    Key differences from Anthropic format:
    - Top-level key: 'parameters' (not 'input_schema')
    - auth_token stripped from properties/required
    - Category enum patched with user's categories
    """
    from backend.output_schemas import ExpenseType

    response = await mcp_client.client.session.list_tools()

    if user_categories:
        category_enum = [cat.get("category_id") for cat in user_categories]
    else:
        category_enum = [e.name for e in ExpenseType]

    tools = []
    for tool in response.tools:
        patched = _patch_category_enum(tool.inputSchema, category_enum)
        props = {k: v for k, v in patched.get("properties", {}).items() if k != "auth_token"}
        required = [r for r in patched.get("required", []) if r != "auth_token"]
        tools.append({
            "type": "function",
            "name": tool.name,
            "description": tool.description or "",
            "parameters": {**patched, "properties": props, "required": required},
        })

    return tools


# ---------------------------------------------------------------------------
# Main relay entry point
# ---------------------------------------------------------------------------

async def handle_realtime_session(watch_ws, user, mcp_client, user_categories: Optional[list], mode: str = "voice"):
    """
    Bridge a single Watch WebSocket session to OpenAI Realtime API.

    Args:
        watch_ws: FastAPI WebSocket connected to the Watch
        user: AuthenticatedUser (provides uid and token)
        mcp_client: ExpenseMCPClient (ready, already started)
        user_categories: User's custom categories (may be None)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")

    if not api_key:
        await _send_watch(watch_ws, {"type": "error", "message": "OpenAI API key not configured"})
        return

    # Build tool list
    try:
        realtime_tools = await _build_realtime_tools(mcp_client, user_categories)
    except Exception as exc:
        logger.exception("Failed to build realtime tool schemas")
        await _send_watch(watch_ws, {"type": "error", "message": f"Tool init failed: {exc}"})
        return

    # Build session instructions
    base_prompt = get_expense_parsing_system_prompt(user_categories)
    instructions = f"{VOICE_PREAMBLE}\n\n{base_prompt}"

    url = f"{OPENAI_REALTIME_URL}?model={model}"
    # GA interface no longer requires the OpenAI-Beta header
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        async with websockets.connect(url, additional_headers=headers) as oai_ws:
            # Send session.update after connection
            # GA interface requires "type": "realtime" to distinguish from transcription sessions
            voice_enabled = mode != "text"
            session_config = {
                "type": "realtime",
                "modalities": ["text", "audio"] if voice_enabled else ["text"],
                "instructions": instructions,
                "input_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": None,
                "tools": realtime_tools,
                "tool_choice": "auto",
            }
            if voice_enabled:
                session_config["voice"] = "alloy"
                session_config["output_audio_format"] = "pcm16"

            await oai_ws.send(json.dumps({
                "type": "session.update",
                "session": session_config,
            }))

            # Run the two I/O loops concurrently
            await asyncio.gather(
                _watch_to_oai(watch_ws, oai_ws),
                _oai_to_watch(watch_ws, oai_ws, user, mcp_client),
            )

    except ConnectionClosed:
        logger.info("OpenAI WS closed")
    except Exception as exc:
        logger.exception("Realtime relay error")
        try:
            await _send_watch(watch_ws, {"type": "error", "message": str(exc)})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Task A: Watch → OpenAI
# ---------------------------------------------------------------------------

async def _watch_to_oai(watch_ws, oai_ws):
    """Forward audio chunks and control messages from Watch to OpenAI."""
    try:
        while True:
            raw = await watch_ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "audio_chunk":
                await oai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": msg["data"],  # base64 PCM16
                }))

            elif msg_type == "audio_done":
                await oai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                await oai_ws.send(json.dumps({"type": "response.create"}))

            elif msg_type == "cancel":
                await oai_ws.send(json.dumps({"type": "input_audio_buffer.clear"}))
                break

    except Exception as exc:
        logger.debug("watch_to_oai ended: %s", exc)


# ---------------------------------------------------------------------------
# Task B: OpenAI → Watch
# ---------------------------------------------------------------------------

async def _oai_to_watch(watch_ws, oai_ws, user, mcp_client):
    """
    Relay OpenAI events to the Watch, executing tool calls along the way.

    Tool call flow:
      response.output_item.done (function_call) → execute tool → conversation.item.create
      response.done with tool calls → response.create (to get verbal summary)
      response.done with no tool calls → send response_done to Watch
    """
    tool_call_counter = 0
    accumulated_text = []
    expense_saved = None

    try:
        async for raw_msg in oai_ws:
            event = json.loads(raw_msg)
            event_type = event.get("type", "")

            # ── Input transcript (user's speech) ──
            if event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                if transcript:
                    await _send_watch(watch_ws, {
                        "type": "input_transcript",
                        "text": transcript,
                    })

            # ── Response text delta ──
            elif event_type == "response.text.delta":
                delta = event.get("delta", "")
                accumulated_text.append(delta)
                await _send_watch(watch_ws, {
                    "type": "response_text_delta",
                    "text": delta,
                })

            # ── Response audio delta ──
            elif event_type == "response.audio.delta":
                await _send_watch(watch_ws, {
                    "type": "response_audio_delta",
                    "data": event.get("delta", ""),
                })

            # ── Function / tool call completed ──
            elif event_type == "response.output_item.done":
                item = event.get("item", {})
                if item.get("type") == "function_call":
                    tool_call_id = item.get("call_id") or item.get("id", "")
                    tool_name = item.get("name", "")
                    raw_args = item.get("arguments", "{}")

                    try:
                        tool_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info("Realtime tool call: %s", tool_name)

                    # Inject auth token
                    if user.token:
                        tool_args = {**tool_args, "auth_token": user.token}

                    # Execute via MCP
                    result_text = await _execute_tool(mcp_client, tool_name, tool_args)

                    # Track save_expense result
                    if tool_name == "save_expense":
                        try:
                            result_data = json.loads(result_text)
                            if result_data.get("success"):
                                expense_saved = {
                                    "success": True,
                                    "message": "",
                                    "expense_id": result_data.get("expense_id"),
                                    "expense_name": result_data.get("expense_name"),
                                    "amount": result_data.get("amount"),
                                    "category": result_data.get("category"),
                                    "budget_warning": result_data.get("budget_warning", ""),
                                }
                        except json.JSONDecodeError:
                            pass

                    # Send tool result back to OpenAI
                    await oai_ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": tool_call_id,
                            "output": result_text,
                        },
                    }))

                    tool_call_counter += 1

            # ── Response completed ──
            elif event_type == "response.done":
                if tool_call_counter > 0:
                    # Model called tools; ask it to generate a verbal summary
                    await oai_ws.send(json.dumps({"type": "response.create"}))
                    tool_call_counter = 0
                else:
                    # No (more) tool calls — deliver final response_done to Watch
                    full_text = "".join(accumulated_text)
                    if expense_saved:
                        expense_saved["message"] = full_text

                    await _send_watch(watch_ws, {
                        "type": "response_done",
                        "expense_saved": expense_saved,
                        "text": full_text,
                    })

                    accumulated_text = []
                    expense_saved = None
                    break

            # ── Error ──
            elif event_type == "error":
                err_msg = event.get("error", {}).get("message", "Unknown OpenAI error")
                logger.error("OpenAI Realtime error: %s", err_msg)
                await _send_watch(watch_ws, {"type": "error", "message": err_msg})
                break

    except Exception as exc:
        logger.debug("oai_to_watch ended: %s", exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _execute_tool(mcp_client, tool_name: str, tool_args: dict) -> str:
    """Execute an MCP tool call and return the result as a string."""
    try:
        result = await mcp_client.client.session.call_tool(tool_name, tool_args)
        if hasattr(result, "content") and result.content:
            if isinstance(result.content, list):
                return "\n".join(
                    block.text if hasattr(block, "text") else str(block)
                    for block in result.content
                )
            return str(result.content)
        return str(result)
    except Exception as exc:
        logger.exception("Tool call failed: %s", tool_name)
        return json.dumps({"error": str(exc)})


async def _send_watch(watch_ws, payload: dict):
    """Send a JSON message to the Watch WebSocket."""
    try:
        await watch_ws.send_text(json.dumps(payload))
    except Exception as exc:
        logger.debug("Failed to send to watch: %s", exc)
