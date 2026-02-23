"""
UnifiedModelClient — routes LLM calls to Anthropic, OpenAI, or Google Gemini.

Supported models:
    claude-sonnet-4-6      (Anthropic)
    claude-haiku-4-5       (Anthropic)
    gpt-5-mini             (OpenAI — Responses API)
    gpt-5.1                (OpenAI — Responses API)
    gemini-3.1-pro-preview (Google Generative AI)
    gemini-3-flash-preview (Google Generative AI)

Tool format convention:
    Anthropic-style input_schema is the canonical format.
    The client converts to provider-specific formats internally.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_MODELS: dict[str, dict] = {
    "claude-sonnet-4-6":      {"provider": "anthropic"},
    "claude-haiku-4-5":       {"provider": "anthropic"},
    "gpt-5-mini":             {"provider": "openai"},
    "gpt-5.1":                {"provider": "openai"},
    "gemini-3.1-pro-preview": {"provider": "google"},
    "gemini-3-flash-preview": {"provider": "google"},
}

DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ModelResponse:
    content: str | None
    tool_calls: list[ToolCall]
    stop_reason: str          # "end_turn" | "tool_use"
    input_tokens: int
    output_tokens: int
    model: str


class UnifiedModelClient:
    """
    Provider-agnostic LLM client.

    For Google Gemini models this client is stateful: it maintains native Gemini
    content history between calls so that thought_signatures embedded in function
    call parts are preserved and replayed verbatim.  The same instance must be
    reused for all turns in a single tool loop (which is already the case in
    _run_non_anthropic_tool_loop).

    Args:
        model: One of the keys in SUPPORTED_MODELS (defaults to DEFAULT_MODEL).
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        if model not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model '{model}'. Choose from: {list(SUPPORTED_MODELS)}"
            )
        self.model = model
        self.provider = SUPPORTED_MODELS[model]["provider"]
        # Native Gemini history (list of content objects / dicts).  Populated
        # after the first _call_google invocation so subsequent calls can replay
        # the raw candidate.content rather than a reconstructed version.
        self._gemini_native_contents: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 2000,
    ) -> ModelResponse:
        """
        Call the appropriate provider and return a normalised ModelResponse.

        Args:
            system:     System prompt string.
            messages:   Message list in Anthropic format
                        (role/content dicts; content may be str or list of blocks).
            tools:      Tool definitions in Anthropic format
                        (name, description, input_schema).
            max_tokens: Maximum tokens to generate.
        """
        if self.provider == "anthropic":
            return self._call_anthropic(system, messages, tools, max_tokens)
        elif self.provider == "openai":
            return self._call_openai(system, messages, tools, max_tokens)
        elif self.provider == "google":
            return self._call_google(system, messages, tools, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _call_anthropic(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int,
    ) -> ModelResponse:
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        response = client.messages.create(
            model=self.model,
            system=system,
            max_tokens=max_tokens,
            messages=messages,
            tools=tools,
        )

        content_text: str | None = None
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        stop_reason = "tool_use" if response.stop_reason == "tool_use" else "end_turn"

        return ModelResponse(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )

    def _call_openai(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int,
    ) -> ModelResponse:
        """
        Call OpenAI via the Responses API (client.responses.create).
        """
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Convert Anthropic-style tools to OpenAI function-calling format
        openai_tools = self._anthropic_tools_to_openai(tools)

        # Convert messages: Anthropic content lists → OpenAI strings
        openai_messages = self._anthropic_messages_to_openai(system, messages)

        response = client.responses.create(
            model=self.model,
            input=openai_messages,
            tools=openai_tools if openai_tools else [],
            max_output_tokens=max_tokens,
        )

        content_text: str | None = None
        tool_calls: list[ToolCall] = []

        for item in response.output:
            item_type = getattr(item, "type", None)
            if item_type == "message":
                # Extract text content from message output
                for content_block in getattr(item, "content", []):
                    block_type = getattr(content_block, "type", None)
                    if block_type == "output_text":
                        content_text = getattr(content_block, "text", None)
            elif item_type == "function_call":
                import json as _json
                arguments_raw = getattr(item, "arguments", "{}")
                try:
                    arguments = _json.loads(arguments_raw) if isinstance(arguments_raw, str) else arguments_raw
                except Exception:
                    arguments = {}
                tool_calls.append(
                    ToolCall(
                        id=getattr(item, "call_id", getattr(item, "id", "")),
                        name=getattr(item, "name", ""),
                        arguments=arguments,
                    )
                )

        stop_reason = "tool_use" if tool_calls else "end_turn"

        return ModelResponse(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )

    def _call_google(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int,
    ) -> ModelResponse:
        """
        Call Google Gemini via the google-genai SDK (google.genai).

        On the first call contents are built by converting the Anthropic-format
        messages.  The raw candidate.content returned by the API is then stored
        in self._gemini_native_contents.  On subsequent calls only the latest
        user message (tool result) is converted and appended — the stored native
        content is replayed verbatim so that thought_signatures embedded in
        function call parts are preserved.
        """
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Add it to your .env file to use Gemini models."
            )

        client = genai.Client(api_key=api_key)

        # Convert Anthropic-style tools to Gemini format
        gemini_tools = self._anthropic_tools_to_gemini(tools)

        # Build the contents list for this request.
        if not self._gemini_native_contents:
            # First call: convert all messages from Anthropic format.
            history, current_parts = self._anthropic_messages_to_gemini(messages)
            all_contents: list = []
            for item in history:
                all_contents.append({
                    "role": item["role"],
                    "parts": [{"text": p} if isinstance(p, str) else p for p in item["parts"]],
                })
            if current_parts:
                all_contents.append({
                    "role": "user",
                    "parts": [{"text": p} if isinstance(p, str) else p for p in current_parts],
                })
        else:
            # Subsequent calls: replay stored native history and append only the
            # new user message (tool result) converted from Anthropic format.
            # This preserves thought_signatures in assistant function call parts.
            last_msg = messages[-1]
            _, new_parts = self._anthropic_messages_to_gemini([last_msg])
            all_contents = list(self._gemini_native_contents)
            if new_parts:
                all_contents.append({
                    "role": "user",
                    "parts": [{"text": p} if isinstance(p, str) else p for p in new_parts],
                })

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=gemini_tools if gemini_tools else None,
            max_output_tokens=max_tokens,
        )

        response = client.models.generate_content(
            model=self.model,
            contents=all_contents,
            config=config,
        )

        content_text: str | None = None
        tool_calls: list[ToolCall] = []

        candidate = response.candidates[0] if response.candidates else None
        if candidate and candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    content_text = part.text
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_calls.append(
                        ToolCall(
                            id=fc.name,  # Gemini doesn't assign IDs; use name
                            name=fc.name,
                            arguments=dict(fc.args),
                        )
                    )

        # Update the stored native history: current contents + raw candidate.
        # This raw candidate.content is replayed verbatim on the next call so
        # that thought_signatures (and other internal metadata) are preserved.
        if candidate and candidate.content:
            self._gemini_native_contents = list(all_contents) + [candidate.content]
        else:
            self._gemini_native_contents = list(all_contents)

        stop_reason = "tool_use" if tool_calls else "end_turn"

        usage = response.usage_metadata
        return ModelResponse(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            model=self.model,
        )

    # ------------------------------------------------------------------
    # Format conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _anthropic_tools_to_openai(tools: list[dict]) -> list[dict]:
        """Convert Anthropic tool definitions → OpenAI function-calling format."""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            })
        return openai_tools

    @staticmethod
    def _anthropic_tools_to_gemini(tools: list[dict]):
        """Convert Anthropic tool definitions → Gemini FunctionDeclaration list."""
        from google.genai import types

        declarations = []
        for tool in tools:
            schema = tool.get("input_schema", {})
            param_schema = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    k: types.Schema(
                        type=_json_type_to_gemini_type(v.get("type", "string")),
                        description=v.get("description", ""),
                    )
                    for k, v in schema.get("properties", {}).items()
                },
                required=schema.get("required", []),
            )
            declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=param_schema,
                )
            )

        return [types.Tool(function_declarations=declarations)] if declarations else []

    @staticmethod
    def _anthropic_messages_to_openai(
        system: str, messages: list[dict]
    ) -> list[dict]:
        """
        Convert Anthropic message list to OpenAI Responses API input format.

        Anthropic content can be a string or a list of typed blocks.
        We flatten everything to plain text for OpenAI.
        """
        result = [{"role": "system", "content": system}]

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if isinstance(content, str):
                result.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Flatten content blocks to text
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            text_parts.append(str(block.get("content", "")))
                        elif block.get("type") == "tool_use":
                            # Skip tool_use blocks — they're handled via function_call output
                            pass
                    else:
                        text_parts.append(str(block))
                combined = "\n".join(text_parts)
                result.append({"role": role, "content": combined})

        return result

    @staticmethod
    def _anthropic_messages_to_gemini(
        messages: list[dict],
    ) -> tuple[list[dict], list]:
        """
        Split Anthropic messages into Gemini chat history + current user parts.

        Converts:
        - tool_use blocks (assistant) → function_call parts
        - tool_result blocks (user)   → function_response parts

        Returns:
            (history, current_parts) where history is a list of
            {'role': ..., 'parts': [...]} and current_parts is the
            latest user message parts list.
        """
        import json as _json

        history = []
        current_parts = []

        for i, msg in enumerate(messages):
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")

            if isinstance(content, str):
                parts = [content]
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            # Assistant requesting a function call
                            parts.append({
                                "function_call": {
                                    "name": block["name"],
                                    "args": block.get("input", {}),
                                }
                            })
                        elif block.get("type") == "tool_result":
                            # User returning function response — Gemini needs a
                            # function_response part; plain text causes an infinite
                            # tool-call loop because the model never sees the result.
                            raw = block.get("content", "")
                            try:
                                response_data = _json.loads(raw) if isinstance(raw, str) else raw
                            except Exception:
                                response_data = {"result": str(raw)}
                            parts.append({
                                "function_response": {
                                    "name": block["tool_use_id"],
                                    "response": response_data,
                                }
                            })
                    else:
                        parts.append(str(block))
            else:
                parts = [str(content)]

            if i < len(messages) - 1:
                history.append({"role": role, "parts": parts})
            else:
                current_parts = parts

        return history, current_parts


def _json_type_to_gemini_type(json_type: str):
    """Map JSON Schema type strings to google.genai types.Type values."""
    from google.genai import types

    mapping = {
        "string":  types.Type.STRING,
        "number":  types.Type.NUMBER,
        "integer": types.Type.INTEGER,
        "boolean": types.Type.BOOLEAN,
        "array":   types.Type.ARRAY,
        "object":  types.Type.OBJECT,
    }
    return mapping.get(json_type, types.Type.STRING)
