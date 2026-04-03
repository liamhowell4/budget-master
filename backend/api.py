"""
FastAPI Backend - Personal Expense Tracker API

Endpoints:
- POST /mcp/process_expense - Process expenses via MCP (text/image/audio)
- GET /expenses - Query expense history with filters
- GET /budget - Get current budget status
- POST /chat/stream - Streaming chat with MCP tools
- GET /health - Health check
"""

import os
import hmac
import logging
from datetime import datetime, date
from typing import Optional, List
import pytz
import base64
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of backend/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)

from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Header, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .firebase_client import FirebaseClient
from .budget_manager import BudgetManager
from .output_schemas import Expense, ExpenseType, Date, CategoryCreate, CategoryUpdate, CategoryReorder
from .recurring_manager import RecurringManager
from .auth import get_current_user, get_optional_user, AuthenticatedUser
from .category_defaults import DEFAULT_CATEGORIES, MAX_CATEGORIES
from .exceptions import DocumentNotFoundError
from .chat_helpers import (
    get_or_create_conversation, build_message_context,
    run_claude_tool_loop, save_conversation_history, ToolLoopResult
)
from .model_client import SUPPORTED_MODELS, DEFAULT_MODEL

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Personal Expense Tracker API",
    description="API for tracking personal expenses via SMS/MMS and Streamlit UI",
    version="2.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware to allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server (default)
        "http://127.0.0.1:5173",
        "http://localhost:5174",   # Admin dashboard
        "http://127.0.0.1:5174",
        "http://localhost:3000",   # React Frontend (alt port)
        "http://127.0.0.1:3000",
        "http://localhost:8000",   # Allow same-origin too
        "http://127.0.0.1:8000",
        "https://happy-pi-day.tail993508.ts.net:5174",  # Admin dashboard (Tailscale)
        "https://happy-pi-day.tail993508.ts.net:5173",  # Frontend (Tailscale)
        "https://happy-pi-day.tail993508.ts.net:3000",  # Frontend alt (Tailscale)
        "https://budget-master-lh.web.app",      # Firebase Hosting (production)
        "https://budget-master-lh.firebaseapp.com",  # Firebase Hosting (alt domain)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Initialize Firebase client and budget manager
firebase_client = FirebaseClient()
budget_manager = BudgetManager(firebase_client)

# MCP Client (initialized on startup)
_mcp_client = None

# Get user timezone
USER_TIMEZONE = pytz.timezone(os.getenv("USER_TIMEZONE", "America/Chicago"))


# ==================== Helpers ====================

def _format_timestamps(data: dict, fields: list = None) -> None:
    """Convert Firestore timestamp objects to ISO format strings in-place."""
    if fields is None:
        fields = ["created_at", "last_activity"]
    for field in fields:
        val = data.get(field)
        if val and hasattr(val, 'isoformat'):
            data[field] = val.isoformat()


def _process_conversation_messages(messages: list[dict]) -> list[dict]:
    """
    Transform raw stored messages into frontend-friendly format.

    The backend stores tool interactions as 3 separate messages:
      1. assistant: content = JSON array of tool_use blocks
      2. user:      content = JSON array of tool_result blocks
      3. assistant: content = final text response

    This function merges them into a single assistant message with:
      - content: the final text response
      - tool_calls: list of {id, name, args, result}

    Synthetic user messages containing only tool_result blocks are dropped.
    """
    processed = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Check if this assistant message contains tool_use blocks
        if role == "assistant" and isinstance(content, str) and content.startswith("["):
            try:
                blocks = json.loads(content)
                if isinstance(blocks, list) and blocks and blocks[0].get("type") == "tool_use":
                    # Extract tool calls from tool_use blocks
                    tool_calls = []
                    for block in blocks:
                        if block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id", ""),
                                "name": block.get("name", ""),
                                "args": block.get("input", {}),
                                "result": None,
                            })

                    # Next message should be user with tool_result blocks
                    if i + 1 < len(messages):
                        next_msg = messages[i + 1]
                        next_content = next_msg.get("content", "")
                        if next_msg.get("role") == "user" and isinstance(next_content, str) and next_content.startswith("["):
                            try:
                                result_blocks = json.loads(next_content)
                                if isinstance(result_blocks, list) and result_blocks and result_blocks[0].get("type") == "tool_result":
                                    # Match results to tool calls
                                    result_map = {
                                        rb.get("tool_use_id"): rb.get("content", "")
                                        for rb in result_blocks
                                        if rb.get("type") == "tool_result"
                                    }
                                    for tc in tool_calls:
                                        result_str = result_map.get(tc["id"], "")
                                        try:
                                            tc["result"] = json.loads(result_str) if result_str else {}
                                        except (json.JSONDecodeError, TypeError):
                                            tc["result"] = result_str
                                    i += 1  # skip the tool_result user message
                            except (json.JSONDecodeError, TypeError):
                                pass

                    # Next message after tool_result should be final assistant text
                    final_text = ""
                    final_timestamp = msg.get("timestamp")
                    content_blocks = None
                    if i + 1 < len(messages) and messages[i + 1].get("role") == "assistant":
                        next_assistant = messages[i + 1]
                        next_content = next_assistant.get("content", "")
                        # Only consume if it's plain text (not another tool_use block)
                        if not (isinstance(next_content, str) and next_content.startswith("[")):
                            final_text = next_content
                            final_timestamp = next_assistant.get("timestamp", final_timestamp)
                            content_blocks = next_assistant.get("content_blocks")
                            i += 1  # skip the final text message (merged)

                    # For old conversations without stored content_blocks,
                    # synthesize them: tool cards first, then summary text.
                    if not content_blocks and tool_calls:
                        content_blocks = []
                        for tc in tool_calls:
                            content_blocks.append({
                                "type": "tool_call",
                                "name": tc["name"],
                                "result": tc.get("result", {}),
                            })
                        if final_text:
                            content_blocks.append({"type": "text", "text": final_text})

                    merged = {
                        "role": "assistant",
                        "content": final_text,
                        "timestamp": final_timestamp,
                        "tool_calls": tool_calls,
                    }
                    if content_blocks:
                        merged["content_blocks"] = content_blocks
                    processed.append(merged)
                    i += 1
                    continue
            except (json.JSONDecodeError, TypeError):
                pass

        # Check for new-format messages that already have content_blocks
        # (stored by the updated save_conversation_history)
        if role == "assistant" and msg.get("content_blocks"):
            processed.append(msg)
            i += 1
            continue

        # Pass through normal messages (strip any accidental tool_result user messages)
        if role == "user" and isinstance(content, str) and content.startswith("["):
            try:
                blocks = json.loads(content)
                if isinstance(blocks, list) and blocks and blocks[0].get("type") == "tool_result":
                    i += 1
                    continue  # skip orphaned tool_result messages
            except (json.JSONDecodeError, TypeError):
                pass

        processed.append(msg)
        i += 1

    return processed


def _summarize_expense_text(text: Optional[str]) -> str:
    """Return a log-safe summary without storing full user-entered expense text."""
    if not text:
        return "empty"

    normalized = " ".join(text.split())
    if len(normalized) > 32:
        normalized = f"{normalized[:32]}..."

    return f"{len(text)} chars: {normalized!r}"


def _parse_date_query(value: Optional[str], field_name: str) -> Optional[date]:
    """Parse YYYY-MM-DD query params into date objects."""
    if value is None:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}. Expected YYYY-MM-DD."
        ) from exc


def _resolve_expense_category_filter(
    user_firebase: FirebaseClient,
    category: Optional[str],
) -> Optional[str]:
    """Resolve a category filter against user categories or legacy enum values."""
    if not category:
        return None

    if user_firebase.has_categories_setup():
        needle = category.lower()
        for cat in user_firebase.get_user_categories():
            category_id = cat.get("category_id", "")
            display_name = cat.get("display_name", "")
            if category_id.lower() == needle or display_name.lower() == needle:
                return category_id

    try:
        return ExpenseType[category.upper()].name
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Valid categories include your configured category IDs plus {[e.name for e in ExpenseType]}"
        ) from exc


async def _ensure_default_chat_server_connected() -> tuple[bool, str | None]:
    """
    Ensure the shared MCP connection is ready for chat requests.

    The mobile apps should not need to manage this shared process themselves.
    """
    from .mcp.connection_manager import get_connection_manager
    from .mcp.server_config import get_server_by_id

    conn_manager = get_connection_manager()
    client = conn_manager.get_client()
    if conn_manager.is_connected and client and client.session:
        return True, None

    server_config = get_server_by_id("expense-server")
    if not server_config:
        return False, "Default expense server is not configured"

    success, _tools, error = await conn_manager.connect(
        server_id=server_config.id,
        server_name=server_config.name,
        server_path=server_config.path,
    )
    return success, error


# ==================== Shared MCP Processing Function ====================

async def process_expense_with_mcp(
    text: str,
    image_base64: Optional[str] = None,
    user_id: str = None,
    auth_token: str = None,
    conversation_id: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Shared MCP processing function for expense parsing.

    Handles text and/or image inputs, processes them via MCP client,
    and returns structured expense data.

    Args:
        text: Text description of expense (can be empty if image provided)
        image_base64: Optional base64-encoded image with data URL prefix
        user_id: Firebase Auth UID for conversation history
        auth_token: Firebase Auth ID token for MCP tool authentication
        conversation_id: Optional conversation ID for context continuity

    Returns:
        dict with keys: success, expense_id, expense_name, amount, category,
        budget_warning, message, conversation_id

    Raises:
        RuntimeError: If MCP client is not initialized
        ValueError: If auth_token is not provided
    """
    if not _mcp_client:
        raise RuntimeError("MCP client not initialized")

    if not auth_token:
        raise ValueError("auth_token is required for authentication")

    logger.info(
        "Processing with MCP: user_id='%s', text_summary=%s, has_image=%s, conversation_id=%s",
        user_id,
        _summarize_expense_text(text),
        image_base64 is not None,
        conversation_id,
    )

    # Call MCP client - pass auth_token for MCP server verification
    result = await _mcp_client.process_expense_message(
        text=text or "",  # Ensure text is never None
        image_base64=image_base64,
        auth_token=auth_token,
        user_id=user_id,
        conversation_id=conversation_id,
        model=model,
    )

    # Ensure message is populated for consistency
    if not result.get("message"):
        # Fallback: construct message from result data
        if result.get("success"):
            name = result.get("expense_name", "expense")
            amount = result.get("amount", 0)
            category = result.get("category", "")
            warning = result.get("budget_warning", "")

            message = f"✅ Saved ${amount:.2f} {name} ({category})"
            if warning:
                message += f"\n{warning}"
            result["message"] = message
        else:
            result["message"] = "❌ Could not parse expense. Please try again."

    return result


# ==================== Recurring Check Logic ====================

async def _check_recurring_expenses_logic(user_firebase: FirebaseClient = None) -> dict:
    """
    Core logic for checking and creating pending expenses from recurring templates.

    Used by both startup event (local dev) and /admin/check-recurring endpoint (production).

    Args:
        user_firebase: User-scoped FirebaseClient. If None, uses global client (legacy).

    Returns:
        dict with created_count, total_recurring, message, and details
    """
    from .recurring_manager import get_today_in_user_timezone

    # Use provided client or fallback to global (legacy mode)
    fb = user_firebase or firebase_client

    # Get all active recurring expenses
    recurring_expenses = fb.get_all_recurring_expenses(active_only=True)

    if not recurring_expenses:
        return {"created_count": 0, "message": "No active recurring expenses found", "details": []}

    # Use timezone-aware today
    today = get_today_in_user_timezone()
    today_date = Date(day=today.day, month=today.month, year=today.year)

    created_count = 0
    details = []

    for recurring in recurring_expenses:
        # Check if we should create a pending expense
        should_create, trigger_date = RecurringManager.should_create_pending(recurring)

        if should_create and trigger_date:
            # Check if pending already exists for this template
            existing_pending = fb.get_pending_by_template(recurring.template_id)

            if existing_pending:
                details.append(f"Skipped {recurring.expense_name} - pending already exists")
                continue

            # Create pending expense
            pending = RecurringManager.create_pending_expense_from_recurring(recurring, trigger_date)
            pending_id = fb.save_pending_expense(pending)

            # Update last_reminded
            fb.update_recurring_expense(
                recurring.template_id,
                {"last_reminded": {
                    "day": today_date.day,
                    "month": today_date.month,
                    "year": today_date.year
                }}
            )

            created_count += 1
            details.append(f"Created pending for {recurring.expense_name} (due {trigger_date.month}/{trigger_date.day})")

    return {
        "created_count": created_count,
        "total_recurring": len(recurring_expenses),
        "message": f"Created {created_count} pending expense(s)" if created_count > 0 else "All recurring expenses up to date",
        "details": details
    }


# ==================== Startup Events ====================

@app.on_event("startup")
async def check_recurring_expenses():
    """
    Check for due recurring expenses on API startup.

    This runs every time the API starts (for local dev convenience).
    In production (Cloud Run), set SKIP_STARTUP_RECURRING_CHECK=true
    and use Cloud Scheduler to call /admin/check-recurring instead.
    """
    # Skip in production - Cloud Scheduler handles this
    if os.getenv("SKIP_STARTUP_RECURRING_CHECK", "").lower() == "true":
        logger.info("Skipping startup recurring check (SKIP_STARTUP_RECURRING_CHECK=true)")
        return

    try:
        logger.info("Checking for due recurring expenses on startup...")
        result = await _check_recurring_expenses_logic()
        logger.info(result['message'])
        for detail in result.get("details", []):
            logger.info("  %s", detail)
    except Exception:
        logger.exception("Error checking recurring expenses")


@app.on_event("startup")
async def startup_mcp():
    """
    Initialize MCP client on startup.

    This spawns the expense_server.py subprocess and connects via stdio.
    Also pre-connects the ConnectionManager so frontend connections are instant.
    """
    global _mcp_client

    try:
        logger.info("Initializing MCP client...")
        from .mcp.client import ExpenseMCPClient

        _mcp_client = ExpenseMCPClient()
        await _mcp_client.startup()
        logger.info("MCP backend ready")
    except Exception:
        logger.exception("Error initializing MCP backend")

    # Pre-connect the ConnectionManager so frontend doesn't wait
    try:
        logger.info("Pre-connecting MCP server for frontend...")
        from .mcp.connection_manager import get_connection_manager
        from .mcp.server_config import get_server_by_id

        server_config = get_server_by_id("expense-server")
        if server_config:
            conn_manager = get_connection_manager()
            success, tools, error = await conn_manager.connect(
                server_id=server_config.id,
                server_name=server_config.name,
                server_path=server_config.path
            )
            if success:
                logger.info("MCP server pre-connected (%d tools available)", len(tools))
            else:
                logger.warning("MCP pre-connection failed: %s", error)
    except Exception as e:
        logger.warning("MCP pre-connection error (non-fatal): %s", e)


# ==================== Pydantic Models ====================

class ExpenseResponse(BaseModel):
    """Response model for expense submission."""
    success: bool
    message: str
    expense_id: Optional[str] = None
    expense_name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    budget_warning: Optional[str] = None
    conversation_id: Optional[str] = None


class BudgetCategory(BaseModel):
    """Budget status for a single category."""
    category: str
    spending: float
    cap: float
    percentage: float
    remaining: float
    emoji: str


class BudgetStatusResponse(BaseModel):
    """Response model for budget status."""
    year: int
    month: int
    month_name: str
    categories: List[BudgetCategory]
    total_spending: float
    total_cap: float
    total_percentage: float
    total_remaining: float
    excluded_categories: List[str] = []  # Category IDs excluded from total calculation
    # Flexible budget period fields (all optional for backward compat)
    period_type: str = "monthly"
    period_start: Optional[str] = None   # ISO date string
    period_end: Optional[str] = None     # ISO date string
    period_label: Optional[str] = None
    days_in_period: Optional[int] = None
    days_elapsed: Optional[int] = None
    monthly_total_cap: Optional[float] = None  # The un-prorated total cap


class BulkBudgetUpdateRequest(BaseModel):
    """Request model for bulk budget cap updates."""
    total_budget: float
    category_budgets: dict[str, float]  # {"FOOD_OUT": 500.0, "RENT": 1200.0, ...}


class BulkBudgetUpdateResponse(BaseModel):
    """Response model for bulk budget cap updates."""
    success: bool
    message: str
    updated_caps: dict[str, float]


# ==================== Endpoints ====================

@app.post("/mcp/process_expense", response_model=ExpenseResponse)
@limiter.limit("30/minute")
async def mcp_process_expense(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    text: Optional[str] = Form(None, description="Text description of expense"),
    image: Optional[UploadFile] = File(None, description="Receipt image"),
    audio: Optional[UploadFile] = File(None, description="Voice recording for transcription"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID for context continuity"),
):
    """
    Process expenses via MCP backend.

    Requires authentication via Firebase Auth token in Authorization header.
    Accepts text, image, and/or audio inputs and processes them via Claude + MCP.

    Args:
        current_user: Authenticated user from Firebase Auth token
        text: Optional text description of expense
        image: Optional receipt image file
        audio: Optional voice recording (WAV, MP3, etc.) for Whisper transcription

    Returns:
        ExpenseResponse with structured expense data
    """
    try:
        # Check if MCP client is initialized
        if not _mcp_client:
            raise HTTPException(
                status_code=503,
                detail="MCP backend not initialized"
            )

        # Transcribe audio if provided
        if audio:
            from .whisper_client import transcribe_audio

            # Validate audio type
            allowed_audio_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/webm", "audio/ogg", "audio/mp4", "audio/x-wav"]
            if audio.content_type and audio.content_type not in allowed_audio_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid audio type. Allowed: {allowed_audio_types}"
                )

            audio_bytes = await audio.read()

            # Enforce file size limit (25 MB max for Whisper)
            max_audio_size = 25 * 1024 * 1024
            if len(audio_bytes) > max_audio_size:
                raise HTTPException(
                    status_code=413,
                    detail="Audio file too large. Maximum size is 25 MB."
                )

            logger.info("Transcribing audio: %d bytes, type: %s", len(audio_bytes), audio.content_type)

            # Sanitize filename to prevent path traversal
            import pathlib
            safe_filename = pathlib.PurePosixPath(audio.filename or "recording.wav").name
            transcription = await transcribe_audio(audio_bytes, safe_filename)
            logger.debug("Transcription: %s", transcription)

            # Combine transcription with text (transcription first, then user text)
            if transcription:
                if text:
                    text = f"{transcription} {text}"
                else:
                    text = transcription

        # Must have at least one input
        if not text and not image:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least one input: text, image, or audio"
            )

        # Process image if provided
        image_base64 = None
        if image:
            # Validate image type
            allowed_types = ["image/jpeg", "image/jpg", "image/png"]
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image type. Allowed: {allowed_types}"
                )

            # Read image bytes
            image_bytes = await image.read()

            # Enforce file size limit (10 MB max)
            max_image_size = 10 * 1024 * 1024
            if len(image_bytes) > max_image_size:
                raise HTTPException(
                    status_code=413,
                    detail="Image file too large. Maximum size is 10 MB."
                )

            # Convert to base64 with data URL prefix
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            # Use the image content type from upload
            image_base64 = f"data:{image.content_type};base64,{image_base64}"

            logger.info("Image uploaded: %d bytes, type: %s", len(image_bytes), image.content_type)

        # Resolve the user's selected model
        user_firebase = FirebaseClient.for_user(current_user.uid)
        user_settings = user_firebase.get_user_settings(current_user.uid)
        selected_model = user_settings.get("selected_model", DEFAULT_MODEL)
        if selected_model not in SUPPORTED_MODELS:
            selected_model = DEFAULT_MODEL

        # Call shared MCP processing function
        # Pass auth_token for MCP server verification (defense in depth)
        result = await process_expense_with_mcp(
            text=text or "",
            image_base64=image_base64,
            user_id=current_user.uid,
            auth_token=current_user.token,
            conversation_id=conversation_id,
            model=selected_model,
        )

        # Return as structured JSON response
        return ExpenseResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            expense_id=result.get("expense_id"),
            expense_name=result.get("expense_name"),
            amount=result.get("amount"),
            category=result.get("category"),
            budget_warning=result.get("budget_warning"),
            conversation_id=result.get("conversation_id")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /mcp/process_expense")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/expenses")
async def get_expenses(
    current_user: AuthenticatedUser = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Get expense history with optional filters.

    Requires authentication via Firebase Auth token.

    Query Parameters:
    - year: Filter by year (e.g., 2025)
    - month: Filter by month (1-12)
    - category: Filter by category (e.g., "FOOD_OUT")
    - start_date/end_date: Optional YYYY-MM-DD date-range filter. When provided,
      both must be present and take precedence over year/month.

    Returns list of expenses matching filters.
    """
    try:
        # Create user-scoped Firebase client
        user_firebase = FirebaseClient.for_user(current_user.uid)

        start_date_obj = _parse_date_query(start_date, "start_date")
        end_date_obj = _parse_date_query(end_date, "end_date")

        if (start_date_obj is None) != (end_date_obj is None):
            raise HTTPException(
                status_code=400,
                detail="start_date and end_date must be provided together"
            )

        if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
            raise HTTPException(
                status_code=400,
                detail="start_date must be on or before end_date"
            )

        # Default to current month if not specified
        if start_date_obj is None and (year is None or month is None):
            now = datetime.now(USER_TIMEZONE)
            year = year or now.year
            month = month or now.month

        category_filter = _resolve_expense_category_filter(user_firebase, category)

        # Get expenses from Firebase (user-scoped)
        if start_date_obj and end_date_obj:
            expenses = user_firebase.get_expenses_in_date_range(
                Date(day=start_date_obj.day, month=start_date_obj.month, year=start_date_obj.year),
                Date(day=end_date_obj.day, month=end_date_obj.month, year=end_date_obj.year),
                category_filter,
            )
            response_year = start_date_obj.year
            response_month = start_date_obj.month
        else:
            expenses = user_firebase.get_monthly_expenses(year, month, category_filter)
            response_year = year
            response_month = month

        return {
            "year": response_year,
            "month": response_month,
            "category": category,
            "start_date": start_date_obj.isoformat() if start_date_obj else None,
            "end_date": end_date_obj.isoformat() if end_date_obj else None,
            "count": len(expenses),
            "expenses": expenses
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in /expenses: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


class ExpenseCreateRequest(BaseModel):
    """Request body for creating an expense directly."""
    expense_name: str
    amount: float
    category: str
    date: dict  # {day: int, month: int, year: int}
    notes: Optional[str] = None


@app.post("/expenses")
async def create_expense(
    expense_data: ExpenseCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create an expense directly without AI processing.

    Requires authentication via Firebase Auth token.

    Request Body:
    - expense_name: Name of the expense
    - amount: Amount in dollars
    - category: Category ID string (e.g., "FOOD_OUT")
    - date: {day, month, year}

    Returns the created expense ID.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        try:
            date_obj = Date(
                day=expense_data.date["day"],
                month=expense_data.date["month"],
                year=expense_data.date["year"]
            )
        except (KeyError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Expected {{day, month, year}}: {e}")

        # Use a dummy ExpenseType for the Expense model; pass category_str override
        try:
            expense_type = ExpenseType[expense_data.category.upper()]
        except KeyError:
            expense_type = list(ExpenseType)[0]  # fallback; overridden by category_str

        expense = Expense(
            expense_name=expense_data.expense_name,
            amount=expense_data.amount,
            date=date_obj,
            category=expense_type
        )

        expense_id = user_firebase.save_expense(
            expense,
            input_type="manual",
            category_str=expense_data.category.upper(),
            notes=expense_data.notes,
        )

        return {"success": True, "expense_id": expense_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in POST /expenses: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/expenses/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Fetch a single expense by ID for live widget hydration/edit flows."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        expense = user_firebase.get_expense_by_id(expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        return {"expense": expense}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in GET /expenses/%s: %s", expense_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Delete an expense by ID.

    Requires authentication via Firebase Auth token.

    Path Parameters:
    - expense_id: The Firestore document ID of the expense to delete

    Returns success status.
    """
    try:
        # Create user-scoped Firebase client
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Delete the expense
        try:
            user_firebase.delete_expense(expense_id)
        except DocumentNotFoundError:
            raise HTTPException(status_code=404, detail="Expense not found")

        return {"success": True, "expense_id": expense_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in DELETE /expenses/%s: %s", expense_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


class ExpenseUpdateRequest(BaseModel):
    """Request body for updating an expense."""
    expense_name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    date: Optional[dict] = None  # {day: int, month: int, year: int}
    timestamp: Optional[str] = None  # ISO 8601 string
    notes: Optional[str] = None


@app.put("/expenses/{expense_id}")
async def update_expense(
    expense_id: str,
    update_data: ExpenseUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update an expense by ID.

    Requires authentication via Firebase Auth token.

    Path Parameters:
    - expense_id: The Firestore document ID of the expense to update

    Request Body:
    - expense_name: New name (optional)
    - amount: New amount (optional)

    Returns success status with updated fields.
    """
    try:
        # Create user-scoped Firebase client
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Parse date dict to Date object if provided
        date_obj = None
        if update_data.date:
            try:
                date_obj = Date(
                    day=update_data.date["day"],
                    month=update_data.date["month"],
                    year=update_data.date["year"]
                )
            except (KeyError, TypeError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date format. Expected {{day, month, year}}: {e}"
                )

        # Parse timestamp ISO string to datetime if provided
        timestamp_dt = None
        if update_data.timestamp:
            try:
                timestamp_dt = datetime.fromisoformat(update_data.timestamp.replace("Z", "+00:00"))
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid timestamp format. Expected ISO 8601: {e}"
                )

        # Update the expense
        try:
            user_firebase.update_expense(
                expense_id=expense_id,
                expense_name=update_data.expense_name,
                amount=update_data.amount,
                category_str=update_data.category,
                date=date_obj,
                timestamp=timestamp_dt,
                notes=(
                    ""
                    if "notes" in update_data.model_fields_set and update_data.notes is None
                    else update_data.notes
                ),
            )
        except DocumentNotFoundError:
            raise HTTPException(status_code=404, detail="Expense not found")

        return {
            "success": True,
            "expense_id": expense_id,
            "updated_fields": {
                k: v for k, v in update_data.model_dump().items() if v is not None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in PUT /expenses/%s: %s", expense_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None,
    period_offset: Optional[int] = None,
):
    """
    Get current budget status for all categories.

    Requires authentication via Firebase Auth token.

    Query Parameters:
    - year: Year to check (defaults to current year, used when period_offset is None)
    - month: Month to check (defaults to current month, used when period_offset is None)
    - period_offset: Navigate by N periods from the current period (+/-). When provided,
                     the user's period settings are used to determine the period type.

    Returns budget data for all categories with spending/cap/percentage.
    Total spending excludes categories marked with exclude_from_total=true.
    """
    from .period_calculator import get_current_period, navigate_period, prorate_cap as calc_prorate_cap
    from calendar import monthrange

    try:
        # Create user-scoped Firebase client and budget manager
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Silent migration if needed
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()

        # Load period settings
        period_settings = user_firebase.get_budget_period_settings(current_user.uid)
        period_type = period_settings.get("budget_period_type", "monthly")
        month_start_day = period_settings.get("budget_month_start_day", 1)
        week_start_day = period_settings.get("budget_week_start_day", "Monday")
        biweekly_anchor = period_settings.get("budget_biweekly_anchor", "2024-01-01")

        if period_offset is not None:
            # Use period-aware navigation
            now = datetime.now(USER_TIMEZONE)
            current_period = get_current_period(
                period_type=period_type,
                month_start_day=month_start_day,
                week_start_day=week_start_day,
                biweekly_anchor=biweekly_anchor,
            )
            # Navigate period_offset steps
            budget_period = current_period
            for _ in range(abs(period_offset)):
                direction = 1 if period_offset > 0 else -1
                budget_period = navigate_period(
                    budget_period,
                    direction=direction,
                    month_start_day=month_start_day,
                    week_start_day=week_start_day,
                    biweekly_anchor=biweekly_anchor,
                )
            year = budget_period.start_date.year
            month = budget_period.start_date.month
            month_name = budget_period.label
        else:
            # Legacy mode: use year/month params
            budget_period = None
            if year is None or month is None:
                now = datetime.now(USER_TIMEZONE)
                year = year or now.year
                month = month or now.month
            month_name = datetime(year, month, 1).strftime("%B %Y")
            # Build a calendar-month period for consistent spending queries
            from .period_calculator import get_current_period as _gcp
            from datetime import date as _date
            budget_period = _gcp(
                period_type="monthly",
                month_start_day=1,
                as_of=_date(year, month, 15),
            )

        # Get user's custom categories
        user_categories = user_firebase.get_user_categories()

        # Get spending by category for the period
        from .output_schemas import Date as DateModel
        start_date = DateModel(
            day=budget_period.start_date.day,
            month=budget_period.start_date.month,
            year=budget_period.start_date.year,
        )
        end_date = DateModel(
            day=budget_period.end_date.day,
            month=budget_period.end_date.month,
            year=budget_period.end_date.year,
        )
        spending_by_category = user_firebase.get_spending_by_category(start_date, end_date)

        # Build category list and track excluded categories
        category_list = []
        excluded_categories = []
        total_spending_filtered = 0.0
        excluded_cap_total_raw = 0.0

        for cat in user_categories:
            category_id = cat["category_id"]
            spending = spending_by_category.get(category_id, 0)
            monthly_cap = cat.get("monthly_cap", 0)
            is_excluded = cat.get("exclude_from_total", False)

            # Prorate cap for non-calendar-month periods
            effective_cap = calc_prorate_cap(monthly_cap, budget_period) if monthly_cap > 0 else 0

            if effective_cap > 0:
                percentage = (spending / effective_cap) * 100
                remaining = effective_cap - spending
            else:
                percentage = 0
                remaining = 0

            category_list.append(BudgetCategory(
                category=category_id,
                spending=spending,
                cap=effective_cap,
                percentage=percentage,
                remaining=remaining,
                emoji=cat.get("icon", "📦")
            ))

            # Track excluded categories and calculate filtered totals
            if is_excluded:
                excluded_categories.append(category_id)
                excluded_cap_total_raw += monthly_cap
            else:
                total_spending_filtered += spending

        # Get total budget cap
        monthly_total_cap_raw = user_firebase.get_total_monthly_budget() or 0
        prorated_excluded = calc_prorate_cap(excluded_cap_total_raw, budget_period) if excluded_cap_total_raw > 0 else 0
        prorated_total = calc_prorate_cap(monthly_total_cap_raw, budget_period) if monthly_total_cap_raw > 0 else 0
        total_cap = prorated_total - prorated_excluded
        total_percentage = (total_spending_filtered / total_cap) * 100 if total_cap > 0 else 0
        total_remaining = total_cap - total_spending_filtered

        return BudgetStatusResponse(
            year=year,
            month=month,
            month_name=month_name,
            categories=category_list,
            total_spending=total_spending_filtered,
            total_cap=total_cap,
            total_percentage=total_percentage,
            total_remaining=total_remaining,
            excluded_categories=excluded_categories,
            period_type=budget_period.period_type,
            period_start=budget_period.start_date.isoformat(),
            period_end=budget_period.end_date.isoformat(),
            period_label=budget_period.label,
            days_in_period=budget_period.days_in_period,
            days_elapsed=budget_period.days_elapsed,
            monthly_total_cap=monthly_total_cap_raw,
        )

    except Exception as e:
        logger.error("Error in /budget: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/budget-caps/bulk-update", response_model=BulkBudgetUpdateResponse)
async def bulk_update_budget_caps(
    request: BulkBudgetUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Bulk update all budget caps.

    Requires authentication via Firebase Auth token.

    Request body:
    {
        "total_budget": 2000.0,
        "category_budgets": {
            "FOOD_OUT": 500.0,
            "RENT": 1200.0,
            "GROCERIES": 150.0,
            ...
        }
    }

    Validates:
    - sum(category_budgets) <= total_budget
    - All category keys are valid ExpenseType enum values

    Updates all budget caps in user's budget_caps/ collection.
    """
    try:
        # Create user-scoped Firebase client
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Validate that sum of category budgets doesn't exceed total
        total_allocated = sum(request.category_budgets.values())

        if total_allocated > request.total_budget:
            raise HTTPException(
                status_code=400,
                detail=f"Sum of category budgets (${total_allocated:.2f}) exceeds total budget (${request.total_budget:.2f})"
            )

        # Validate all category names are valid ExpenseType enums
        valid_categories = {expense_type.name for expense_type in ExpenseType}
        invalid_categories = set(request.category_budgets.keys()) - valid_categories

        if invalid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category names: {', '.join(invalid_categories)}"
            )

        # Update total budget cap (user-scoped)
        user_firebase.set_budget_cap("TOTAL", request.total_budget)

        # Update all category budget caps (user-scoped)
        for category, amount in request.category_budgets.items():
            user_firebase.set_budget_cap(category, amount)

        # Return updated caps
        all_caps = user_firebase.get_all_budget_caps()

        return BulkBudgetUpdateResponse(
            success=True,
            message=f"Successfully updated {len(request.category_budgets)} category budgets and total budget",
            updated_caps=all_caps
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception("Error in /budget-caps/bulk-update")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Category Endpoints ====================

@app.get("/categories")
async def get_categories(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get all categories for the authenticated user.

    Performs silent migration from budget_caps if needed.
    Returns list of categories sorted by sort_order.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Silent migration if needed
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()

        categories = user_firebase.get_user_categories()
        total_budget = user_firebase.get_total_monthly_budget()

        return {
            "categories": categories,
            "total_monthly_budget": total_budget,
            "max_categories": MAX_CATEGORIES
        }
    except Exception as e:
        logger.exception("Error in GET /categories")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/categories")
async def create_category(
    category: CategoryCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create a new category for the authenticated user.

    Validates:
    - Max 15 categories
    - Unique name (case-insensitive)
    - Cap <= available budget
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Ensure categories are set up
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()

        # Check available budget against the OTHER category cap.
        # OTHER is the auto-recalculated remainder (total - sum of all non-OTHER caps),
        # so the new cap must fit within what OTHER currently holds.
        categories = user_firebase.get_user_categories()
        other_category = next((cat for cat in categories if cat.get("category_id") == "OTHER"), None)
        other_cap = other_category.get("monthly_cap", 0) if other_category else 0

        if category.monthly_cap > other_cap:
            raise HTTPException(
                status_code=400,
                detail=f"Monthly cap ${category.monthly_cap:.2f} exceeds available Other budget ${other_cap:.2f}"
            )

        # Create category
        category_id = user_firebase.create_category({
            "display_name": category.display_name,
            "icon": category.icon,
            "color": category.color,
            "monthly_cap": category.monthly_cap
        })

        # Recalculate OTHER cap
        user_firebase.recalculate_other_cap()

        return {
            "success": True,
            "category_id": category_id,
            "message": f"Created category '{category.display_name}'"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in POST /categories")
        raise HTTPException(status_code=500, detail="Internal server error")


# NOTE: /categories/reorder and /categories/defaults MUST be before /categories/{category_id}
# otherwise FastAPI will match "reorder" and "defaults" as category IDs

@app.put("/categories/reorder")
async def reorder_categories(
    reorder: CategoryReorder,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update the sort order of categories.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        success = user_firebase.reorder_categories(reorder.category_ids)

        return {
            "success": success,
            "message": "Categories reordered"
        }
    except Exception as e:
        logger.exception("Error in PUT /categories/reorder")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/categories/defaults")
async def get_default_categories():
    """
    Get the list of default categories (for new user setup).

    Does not require authentication.
    """
    defaults = []
    for category_id, config in DEFAULT_CATEGORIES.items():
        defaults.append({
            "category_id": category_id,
            "display_name": config.get("display_name", category_id),
            "icon": config.get("icon", "circle"),
            "color": config.get("color", "#6B7280"),
            "description": config.get("description", ""),
            "is_system": config.get("is_system", False)
        })

    return {
        "defaults": defaults,
        "max_categories": MAX_CATEGORIES
    }


@app.put("/categories/{category_id}")
async def update_category(
    category_id: str,
    updates: CategoryUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update a category for the authenticated user.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Get existing category
        existing = user_firebase.get_category(category_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Category not found")

        # If updating monthly_cap, validate against available budget
        if updates.monthly_cap is not None:
            total_budget = user_firebase.get_total_monthly_budget()
            categories = user_firebase.get_user_categories()

            # Calculate allocated (excluding this category)
            allocated = sum(
                cat.get("monthly_cap", 0)
                for cat in categories
                if cat.get("category_id") != category_id
            )
            available = total_budget - allocated

            if updates.monthly_cap > available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Monthly cap ${updates.monthly_cap:.2f} exceeds available budget ${available:.2f}"
                )

        # Update category
        update_dict = updates.model_dump(exclude_none=True)
        try:
            user_firebase.update_category(category_id, update_dict)
        except DocumentNotFoundError:
            raise HTTPException(status_code=404, detail="Category not found")

        # Recalculate OTHER cap if monthly_cap was updated
        if updates.monthly_cap is not None:
            user_firebase.recalculate_other_cap()

        return {
            "success": True,
            "category_id": category_id,
            "message": "Category updated"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in PUT /categories/%s", category_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    reassign_to: str = "OTHER"
):
    """
    Delete a category and reassign its expenses.

    Query Parameters:
    - reassign_to: Category to reassign expenses to (default: OTHER)
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Verify reassign_to category exists
        if reassign_to != "OTHER":
            target = user_firebase.get_category(reassign_to)
            if not target:
                raise HTTPException(
                    status_code=400,
                    detail=f"Target category '{reassign_to}' not found"
                )

        # Delete category
        reassigned_count = user_firebase.delete_category(category_id, reassign_to)

        # Recalculate OTHER cap
        user_firebase.recalculate_other_cap()

        return {
            "success": True,
            "category_id": category_id,
            "reassigned_count": reassigned_count,
            "reassigned_to": reassign_to,
            "message": f"Deleted category, reassigned {reassigned_count} expense(s) to {reassign_to}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in DELETE /categories/%s", category_id)
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Total Budget Endpoints ====================

@app.get("/budget/total")
async def get_total_budget(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get the user's total monthly budget.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Ensure categories are set up
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()

        total_budget = user_firebase.get_total_monthly_budget()
        categories = user_firebase.get_user_categories()
        allocated = sum(cat.get("monthly_cap", 0) for cat in categories)

        return {
            "total_monthly_budget": total_budget,
            "allocated": allocated,
            "available": total_budget - allocated
        }
    except Exception as e:
        logger.exception("Error in GET /budget/total")
        raise HTTPException(status_code=500, detail="Internal server error")


class TotalBudgetUpdate(BaseModel):
    """Request model for updating total budget."""
    total_monthly_budget: float


@app.put("/budget/total")
async def update_total_budget(
    update: TotalBudgetUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update the user's total monthly budget.

    Recalculates OTHER category cap.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Ensure categories are set up
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()

        if update.total_monthly_budget < 0:
            raise HTTPException(
                status_code=400,
                detail="Total budget must be non-negative"
            )

        # Update total budget
        user_firebase.set_total_monthly_budget(update.total_monthly_budget)

        # Recalculate OTHER cap
        other_cap = user_firebase.recalculate_other_cap()

        return {
            "success": True,
            "total_monthly_budget": update.total_monthly_budget,
            "other_cap": other_cap,
            "message": "Total budget updated"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in PUT /budget/total")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Onboarding Endpoints ====================

class CustomCategoryInput(BaseModel):
    """Input model for a custom category during onboarding."""
    display_name: str
    icon: str
    color: str
    monthly_cap: float = 0


class OnboardingCompleteRequest(BaseModel):
    """Request model for completing onboarding."""
    total_budget: float
    selected_category_ids: List[str]
    category_caps: dict  # Dict[str, float] - category_id -> cap
    custom_categories: Optional[List[CustomCategoryInput]] = None
    excluded_category_ids: List[str] = []
    # Budget period settings (all optional, default to monthly)
    budget_period_type: str = "monthly"
    budget_month_start_day: int = Field(default=1, ge=1, le=28)
    budget_week_start_day: str = "Monday"
    budget_biweekly_anchor: str = "2024-01-01"

    @field_validator("budget_period_type")
    @classmethod
    def validate_budget_period_type(cls, v: str) -> str:
        if v not in ("monthly", "weekly", "biweekly"):
            raise ValueError("budget_period_type must be 'monthly', 'weekly', or 'biweekly'")
        return v

    @field_validator("budget_biweekly_anchor")
    @classmethod
    def validate_biweekly_anchor(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("budget_biweekly_anchor must be a valid date in YYYY-MM-DD format")
        return v


@app.post("/onboarding/complete")
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Complete the onboarding wizard by setting up budget and categories.

    1. Set total monthly budget
    2. Initialize selected categories from defaults
    3. Create any custom categories
    4. Update caps for each category
    5. Recalculate OTHER cap for unallocated budget
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Validate total budget
        if request.total_budget <= 0:
            raise HTTPException(
                status_code=400,
                detail="Total budget must be greater than 0"
            )

        # Calculate total caps including custom categories
        total_caps = sum(request.category_caps.values())
        if request.custom_categories:
            total_caps += sum(c.monthly_cap for c in request.custom_categories)

        if total_caps > request.total_budget:
            raise HTTPException(
                status_code=400,
                detail=f"Category caps (${total_caps:.2f}) exceed total budget (${request.total_budget:.2f})"
            )

        # Initialize categories with selected defaults
        user_firebase.initialize_default_categories(
            total_budget=request.total_budget,
            selected_ids=request.selected_category_ids
        )

        # Update caps for default categories
        for category_id, cap in request.category_caps.items():
            # Skip custom category IDs (they start with CUSTOM_)
            if not category_id.startswith("CUSTOM_"):
                try:
                    user_firebase.update_category(category_id, {"monthly_cap": cap})
                except DocumentNotFoundError:
                    logger.warning("Category %s not found during onboarding cap update", category_id)

        # Create custom categories
        custom_created = 0
        if request.custom_categories:
            for custom in request.custom_categories:
                user_firebase.create_category({
                    "display_name": custom.display_name,
                    "icon": custom.icon,
                    "color": custom.color,
                    "monthly_cap": custom.monthly_cap
                })
                custom_created += 1

        # Set exclude_from_total for any categories the user opted out of total tracking
        for cat_id in request.excluded_category_ids:
            try:
                user_firebase.update_category(cat_id, {"exclude_from_total": True})
            except Exception as e:
                logger.warning("Could not set exclude_from_total for %s: %s", cat_id, e)

        # Recalculate OTHER cap (gets the unallocated budget)
        other_cap = user_firebase.recalculate_other_cap()

        # Save budget period settings
        user_firebase.set_budget_period_settings(current_user.uid, {
            "budget_period_type": request.budget_period_type,
            "budget_month_start_day": request.budget_month_start_day,
            "budget_week_start_day": request.budget_week_start_day,
            "budget_biweekly_anchor": request.budget_biweekly_anchor,
        })

        return {
            "success": True,
            "total_budget": request.total_budget,
            "categories_created": len(request.selected_category_ids) + custom_created,
            "other_cap": other_cap,
            "message": "Onboarding complete! Your budget is set up."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in POST /onboarding/complete")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Recurring Expense Endpoints ====================

@app.get("/recurring")
async def get_recurring_expenses(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get all recurring expense templates. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        recurring_expenses = user_firebase.get_all_recurring_expenses(active_only=False)

        # Convert to dict format for JSON response
        result = []
        for rec in recurring_expenses:
            result.append({
                "template_id": rec.template_id,
                "expense_name": rec.expense_name,
                "amount": rec.amount,
                "category": rec.category.name,
                "frequency": rec.frequency.value,
                "day_of_month": rec.day_of_month,
                "day_of_week": rec.day_of_week,
                "last_of_month": rec.last_of_month,
                "active": rec.active,
                "last_reminded": {
                    "day": rec.last_reminded.day,
                    "month": rec.last_reminded.month,
                    "year": rec.last_reminded.year
                } if rec.last_reminded else None,
                "last_user_action": {
                    "day": rec.last_user_action.day,
                    "month": rec.last_user_action.month,
                    "year": rec.last_user_action.year
                } if rec.last_user_action else None
            })

        return {"recurring_expenses": result}
    except Exception as e:
        logger.error("Error in /recurring: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/pending")
async def get_pending_expenses(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get all pending expenses awaiting confirmation. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        pending_expenses = user_firebase.get_all_pending_expenses(awaiting_only=True)
        return {"pending_expenses": pending_expenses}
    except Exception as e:
        logger.error("Error in /pending: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/pending/{pending_id}/confirm")
async def confirm_pending_expense(
    pending_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    adjusted_amount: Optional[float] = None
):
    """Confirm a pending expense and save it as a regular expense. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Get pending expense
        pending = user_firebase.get_pending_expense(pending_id)
        if not pending:
            raise HTTPException(status_code=404, detail="Pending expense not found")

        # Convert to expense
        expense = RecurringManager.pending_to_expense(pending, adjusted_amount)

        # Save expense
        doc_id = user_firebase.save_expense(expense, input_type="recurring")

        # Update recurring template's last_user_action
        if pending.template_id:
            today = date.today()
            try:
                user_firebase.update_recurring_expense(
                    pending.template_id,
                    {"last_user_action": {
                        "day": today.day,
                        "month": today.month,
                        "year": today.year
                    }}
                )
            except Exception as e:
                logger.warning("Could not update recurring template %s: %s", pending.template_id, e)

        # Delete pending expense
        user_firebase.delete_pending_expense(pending_id)

        return {"success": True, "expense_id": doc_id, "message": "Expense confirmed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in /pending/%s/confirm: %s", pending_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/pending/{pending_id}")
async def delete_pending_expense(
    pending_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Skip/delete a pending expense. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)

        # Get pending to find template_id
        pending_dict = user_firebase.get_all_pending_expenses(awaiting_only=False)
        template_id = None
        for p in pending_dict:
            if p.get("pending_id") == pending_id:
                template_id = p.get("template_id")
                break

        if template_id:
            # Update last_user_action
            today = date.today()
            today_date = Date(day=today.day, month=today.month, year=today.year)
            user_firebase.update_recurring_expense(
                template_id,
                {"last_user_action": {
                    "day": today_date.day,
                    "month": today_date.month,
                    "year": today_date.year
                }}
            )

        # Delete pending expense
        user_firebase.delete_pending_expense(pending_id)

        return {"success": True, "message": "Pending expense deleted"}
    except Exception as e:
        logger.error("Error in /pending/%s: %s", pending_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/recurring/{template_id}")
async def delete_recurring_template(
    template_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete/deactivate a recurring expense template. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        user_firebase.delete_recurring_expense(template_id)
        return {"success": True, "message": "Recurring expense deleted"}
    except Exception as e:
        logger.error("Error in /recurring/%s: %s", template_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Conversation History Endpoints ====================

@app.get("/conversations")
async def list_conversations(
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 20
):
    """
    List recent conversations for the authenticated user.

    Query Parameters:
    - limit: Maximum number of conversations to return (default 20)

    Returns list of conversations ordered by last activity (most recent first).
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        conversations = user_firebase.list_conversations(limit=limit)

        # Format timestamps for JSON serialization
        for conv in conversations:
            _format_timestamps(conv)

        return {"conversations": conversations}
    except Exception as e:
        logger.error("Error in /conversations: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get a specific conversation by ID.

    Returns the conversation with all messages and metadata.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        conversation = user_firebase.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Format timestamps for JSON serialization
        _format_timestamps(conversation)

        # Process messages: merge tool_use/tool_result blocks into
        # frontend-friendly format with separate content and tool_calls
        if "messages" in conversation:
            conversation["messages"] = _process_conversation_messages(
                conversation["messages"]
            )

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in GET /conversations/%s: %s", conversation_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


class DeletedExpenseRequest(BaseModel):
    """Request model for marking an expense as deleted in a conversation."""
    expense_id: str


@app.post("/conversations/{conversation_id}/deleted-expenses")
async def add_deleted_expense(
    conversation_id: str,
    request: DeletedExpenseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Mark an expense as deleted within a conversation.

    Appends the expense_id to the conversation's deleted_expense_ids array
    so the frontend can render the expense card as deleted on reload.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        try:
            user_firebase.add_deleted_expense_to_conversation(
                conversation_id, request.expense_id
            )
        except DocumentNotFoundError:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in POST /conversations/%s/deleted-expenses: %s", conversation_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


class VerifyExpensesRequest(BaseModel):
    """Request model for verifying expense existence."""
    expense_ids: List[str]


@app.post("/expenses/verify")
async def verify_expenses(
    request: VerifyExpensesRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Verify which expense IDs still exist in Firestore.

    Returns the subset of provided IDs that still exist.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        existing_ids = user_firebase.verify_expenses_exist(request.expense_ids)

        return {"existing_ids": existing_ids}
    except Exception as e:
        logger.error("Error in POST /expenses/verify: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a specific conversation. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        try:
            user_firebase.delete_conversation(conversation_id)
        except DocumentNotFoundError:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in DELETE /conversations/%s: %s", conversation_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/conversations")
async def create_conversation(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create a new conversation.

    Returns the new conversation ID.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        conversation_id = user_firebase.create_conversation()
        return {"conversation_id": conversation_id}
    except Exception as e:
        logger.error("Error in POST /conversations: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Admin Endpoints ====================

# Load admin API key from environment
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


@app.post("/admin/check-recurring")
@limiter.limit("5/minute")
async def admin_check_recurring(request: Request, x_api_key: Optional[str] = Header(None)):
    """
    Check for due recurring expenses and create pending expenses for ALL users.

    This endpoint is designed to be called by Cloud Scheduler daily.
    Requires ADMIN_API_KEY header for authentication.

    Headers:
        X-API-Key: The admin API key (must match ADMIN_API_KEY env var)

    Returns:
        JSON with total created_count and per-user details
    """
    # Verify API key
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_API_KEY not configured on server"
        )

    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-API-Key header"
        )

    try:
        logger.info("[Admin] Checking for due recurring expenses for all users...")

        # Get all user IDs from the users collection
        from google.cloud import firestore as gc_firestore
        users_ref = firebase_client.db.collection("users")
        user_docs = users_ref.stream()

        total_created = 0
        all_details = []
        users_checked = 0

        for user_doc in user_docs:
            user_id = user_doc.id
            users_checked += 1
            logger.debug("Checking user: %s", user_id)

            user_firebase = FirebaseClient.for_user(user_id)
            result = await _check_recurring_expenses_logic(user_firebase)

            total_created += result.get("created_count", 0)
            if result.get("details"):
                all_details.extend([f"[{user_id}] {d}" for d in result["details"]])

        message = f"Checked {users_checked} user(s), created {total_created} pending expense(s)"
        logger.info("[Admin] %s", message)

        return {
            "created_count": total_created,
            "users_checked": users_checked,
            "message": message,
            "details": all_details
        }
    except Exception as e:
        logger.exception("[Admin] Error checking recurring expenses")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/cleanup-conversations")
@limiter.limit("5/minute")
async def admin_cleanup_conversations(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    ttl_hours: int = 1440  # 60 days default (60 * 24 = 1440 hours)
):
    """
    Delete old conversations for ALL users.

    This endpoint is designed to be called by Cloud Scheduler daily.
    Requires ADMIN_API_KEY header for authentication.

    Headers:
        X-API-Key: The admin API key (must match ADMIN_API_KEY env var)

    Query Parameters:
        ttl_hours: Delete conversations older than this many hours (default 1440 = 60 days)

    Returns:
        JSON with total deleted count and per-user details
    """
    # Verify API key
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_API_KEY not configured on server"
        )

    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-API-Key header"
        )

    try:
        logger.info("[Admin] Cleaning up conversations older than %d hours...", ttl_hours)
        results = FirebaseClient.cleanup_all_users_conversations(ttl_hours=ttl_hours)

        total_deleted = results.pop("_total", 0)
        message = f"Deleted {total_deleted} old conversation(s)"
        logger.info("[Admin] %s", message)

        return {
            "deleted_count": total_deleted,
            "ttl_hours": ttl_hours,
            "message": message,
            "per_user": results
        }
    except Exception as e:
        logger.exception("[Admin] Error cleaning up conversations")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/admin/users")
@limiter.limit("5/minute")
async def admin_get_users(request: Request, x_api_key: Optional[str] = Header(None)):
    """
    Get all Firebase Auth users.
    Returns list of {uid, email, display_name, photo_url, last_sign_in, created_at}.
    Requires X-API-Key header.
    """
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not configured on server")
    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")

    try:
        import firebase_admin.auth as firebase_auth_mod
        users = []
        page = firebase_auth_mod.list_users()
        while page:
            for user in page.users:
                users.append({
                    "uid": user.uid,
                    "email": user.email,
                    "display_name": user.display_name,
                    "photo_url": user.photo_url,
                    "last_sign_in": user.user_metadata.last_sign_in_timestamp if user.user_metadata else None,
                    "created_at": user.user_metadata.creation_timestamp if user.user_metadata else None,
                })
            page = page.get_next_page()
        return {"users": users}
    except Exception as e:
        logger.exception("[Admin] Error listing users")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/admin/analytics")
@limiter.limit("5/minute")
async def admin_get_analytics(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    days: int = 30
):
    """
    Get usage analytics across all users.
    Returns token_usage docs, extracted tool_calls, and summary stats.
    Requires X-API-Key header.
    """
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not configured on server")
    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")

    try:
        # Use a global (no user_id) FirebaseClient for collection group queries
        global_firebase = FirebaseClient()
        token_usage = global_firebase.get_all_token_usage(days=days)
        conversations = global_firebase.get_all_conversations(days=days)

        # Extract tool calls from conversation messages
        tool_calls = []
        for conv in conversations:
            uid = conv.get('uid', 'unknown')
            conv_id = conv.get('conversation_id', '')
            messages = conv.get('messages', [])
            for msg in messages:
                # Each message may have tool_calls list: [{id, name, args, result}]
                for tc in msg.get('tool_calls', []):
                    tool_name = tc.get('name', '')
                    if tool_name:
                        tool_calls.append({
                            "uid": uid,
                            "tool_name": tool_name,
                            "conversation_id": conv_id,
                            "timestamp": msg.get('timestamp'),
                        })

        # Build summary
        total_input = sum(d.get('input_tokens', 0) for d in token_usage)
        total_output = sum(d.get('output_tokens', 0) for d in token_usage)
        unique_users = len(set(d.get('uid') for d in token_usage))

        return {
            "token_usage": token_usage,
            "tool_calls": tool_calls,
            "summary": {
                "total_api_calls": len(token_usage),
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "unique_users": unique_users,
                "date_range_days": days,
            }
        }
    except Exception as e:
        logger.exception("[Admin] Error fetching analytics")
        raise HTTPException(status_code=500, detail="Internal server error")


class AdminChatRequest(BaseModel):
    """Request model for admin chat."""
    message: str
    history: List[dict] = []
    context: dict = {}


@app.post("/admin/chat")
@limiter.limit("10/minute")
async def admin_chat(
    request: Request,
    body: AdminChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Streaming chat endpoint for the admin dashboard.
    Answers natural language questions about aggregate usage data.
    Requires X-API-Key header.
    """
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not configured on server")
    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")

    import anthropic

    system_prompt = (
        "You are an analytics assistant for a personal finance app's admin dashboard. "
        "You have access to aggregate usage data below. Answer questions about token usage, "
        "API calls, tool usage, endpoint usage, and trends. Keep answers concise and data-driven. "
        "Never reference individual users by name or UID.\n\n"
        f"Dashboard Data:\n{json.dumps(body.context, indent=2)}"
    )

    # Build messages from history + current message
    messages = [{"role": m["role"], "content": m["content"]} for m in body.history]
    messages.append({"role": "user", "content": body.message})

    async def event_stream():
        try:
            client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            async with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.exception("[Admin] Error in admin chat stream")
            yield f"data: {json.dumps({'error': 'An unexpected error occurred'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ==================== User Settings Endpoints ====================

class UserSettingsResponse(BaseModel):
    """Response model for user settings."""
    selected_model: str
    budget_period_type: str = "monthly"
    budget_month_start_day: int = 1
    budget_week_start_day: str = "Monday"
    budget_biweekly_anchor: str = "2024-01-01"


class UserSettingsUpdateRequest(BaseModel):
    """Request model for updating user settings."""
    selected_model: Optional[str] = None
    budget_period_type: Optional[str] = None
    budget_month_start_day: Optional[int] = Field(default=None, ge=1, le=28)
    budget_week_start_day: Optional[str] = None
    budget_biweekly_anchor: Optional[str] = None

    @field_validator("budget_biweekly_anchor")
    @classmethod
    def validate_biweekly_anchor(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("budget_biweekly_anchor must be a valid date in YYYY-MM-DD format")
        return v


@app.get("/user/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get settings for the authenticated user.

    Returns model preference and budget period configuration.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        settings = user_firebase.get_user_settings(current_user.uid)
        selected_model = settings.get("selected_model", DEFAULT_MODEL)
        if selected_model not in SUPPORTED_MODELS:
            selected_model = DEFAULT_MODEL
        period_settings = user_firebase.get_budget_period_settings(current_user.uid)
        return UserSettingsResponse(
            selected_model=selected_model,
            budget_period_type=period_settings.get("budget_period_type", "monthly"),
            budget_month_start_day=period_settings.get("budget_month_start_day", 1),
            budget_week_start_day=period_settings.get("budget_week_start_day", "Monday"),
            budget_biweekly_anchor=period_settings.get("budget_biweekly_anchor", "2024-01-01"),
        )
    except Exception as e:
        logger.exception("Error in GET /user/settings")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/user/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    body: UserSettingsUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update settings for the authenticated user.

    All fields are optional. Validates selected_model against SUPPORTED_MODELS.
    """
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        updates: dict = {}

        if body.selected_model is not None:
            if body.selected_model not in SUPPORTED_MODELS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported model '{body.selected_model}'. "
                           f"Choose from: {list(SUPPORTED_MODELS)}"
                )
            updates["selected_model"] = body.selected_model

        period_updates: dict = {}
        if body.budget_period_type is not None:
            if body.budget_period_type not in ("monthly", "weekly", "biweekly"):
                raise HTTPException(
                    status_code=400,
                    detail="budget_period_type must be 'monthly', 'weekly', or 'biweekly'"
                )
            period_updates["budget_period_type"] = body.budget_period_type
        if body.budget_month_start_day is not None:
            period_updates["budget_month_start_day"] = body.budget_month_start_day
        if body.budget_week_start_day is not None:
            period_updates["budget_week_start_day"] = body.budget_week_start_day
        if body.budget_biweekly_anchor is not None:
            period_updates["budget_biweekly_anchor"] = body.budget_biweekly_anchor

        if updates:
            user_firebase.update_user_settings(current_user.uid, updates)
        if period_updates:
            user_firebase.set_budget_period_settings(current_user.uid, period_updates)

        # Return current state
        settings = user_firebase.get_user_settings(current_user.uid)
        selected_model = settings.get("selected_model", DEFAULT_MODEL)
        if selected_model not in SUPPORTED_MODELS:
            selected_model = DEFAULT_MODEL
        period_settings = user_firebase.get_budget_period_settings(current_user.uid)
        return UserSettingsResponse(
            selected_model=selected_model,
            budget_period_type=period_settings.get("budget_period_type", "monthly"),
            budget_month_start_day=period_settings.get("budget_month_start_day", 1),
            budget_week_start_day=period_settings.get("budget_week_start_day", "Monday"),
            budget_biweekly_anchor=period_settings.get("budget_biweekly_anchor", "2024-01-01"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in PUT /user/settings")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": app.version,
        "endpoints": [
            "/health",
            "/mcp/process_expense",
            "/chat/stream",
            "/ws/realtime",
        ],
    }


# ==================== MCP Chat Frontend Endpoints ====================

@app.get("/servers")
async def list_servers(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    List all available MCP servers.

    Returns list of server configurations that can be connected to.
    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.server_config import get_available_servers

    servers = get_available_servers()

    return [
        {
            "id": server.id,
            "name": server.name,
            "description": server.description
        }
        for server in servers
    ]


@app.post("/connect/{server_id}")
async def connect_to_server(
    server_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Connect to a specific MCP server.

    If already connected to the requested server, returns existing connection.
    Otherwise disconnects from current server (if any) and establishes connection
    to the requested server. Returns tools available on the server.

    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.server_config import get_server_by_id
    from .mcp.connection_manager import get_connection_manager

    # Get server configuration
    server_config = get_server_by_id(server_id)
    if not server_config:
        raise HTTPException(
            status_code=404,
            detail=f"Server '{server_id}' not found"
        )

    # Get connection manager
    conn_manager = get_connection_manager()

    # If already connected to this server, return existing connection (fast path)
    if conn_manager.is_connected and conn_manager.state.server_id == server_id:
        return {
            "success": True,
            "server_id": conn_manager.state.server_id,
            "server_name": conn_manager.state.server_name,
            "tools": conn_manager.state.tools
        }

    # Connect to server
    success, tools, error = await conn_manager.connect(
        server_id=server_config.id,
        server_name=server_config.name,
        server_path=server_config.path
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail=error or "Failed to connect to server"
        )

    # Return success response
    return {
        "success": True,
        "server_id": server_config.id,
        "server_name": server_config.name,
        "tools": tools
    }


@app.get("/status")
async def get_connection_status(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get current MCP server connection status.

    Returns connection state including server ID and available tools.
    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.connection_manager import get_connection_manager

    conn_manager = get_connection_manager()
    state = conn_manager.state

    if state.connected:
        return {
            "connected": True,
            "server_id": state.server_id,
            "tools": state.tools
        }
    else:
        return {
            "connected": False,
            "server_id": None,
            "tools": []
        }


@app.post("/disconnect")
async def disconnect_from_server(
    current_user: AuthenticatedUser = Depends(get_current_user),
    x_api_key: Optional[str] = Header(None),
):
    """
    Disconnect from current MCP server.

    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.connection_manager import get_connection_manager

    conn_manager = get_connection_manager()

    # Only admin callers may tear down the shared MCP process.
    if ADMIN_API_KEY and x_api_key and hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        await conn_manager.disconnect()
        return {"success": True, "message": "Shared MCP server disconnected"}

    logger.info("Ignoring non-admin disconnect request for shared MCP server: uid=%s", current_user.uid)
    return {
        "success": True,
        "message": "Shared MCP server remains connected",
    }


class ChatMessage(BaseModel):
    """Request model for chat messages."""
    message: str
    conversation_id: Optional[str] = None
    model_override: Optional[str] = None


@app.post("/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(
    request: Request,
    chat_message: ChatMessage,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Process a chat message and stream response with tool calls.

    Requires authentication via Firebase Auth token.

    Uses Server-Sent Events (SSE) to stream:
    - conversation_id event at start (for frontend to track)
    - tool_start events when tools begin execution
    - tool_end events when tools finish
    - text events for response chunks
    - [DONE] signal when complete
    - [ERROR] signal on errors

    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.connection_manager import get_connection_manager

    conn_manager = get_connection_manager()

    # Ensure the default shared chat server is ready.
    success, error = await _ensure_default_chat_server_connected()
    if not success:
        async def error_stream():
            yield f"data: [ERROR] {error or 'MCP server unavailable'}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Get client and tools
    client = conn_manager.get_client()
    if not client or not client.session:
        async def error_stream():
            yield "data: [ERROR] MCP client not initialized\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Set up user-scoped Firebase client
    user_firebase = FirebaseClient.for_user(current_user.uid)

    # Resolve the user's selected model
    user_settings = user_firebase.get_user_settings(current_user.uid)
    selected_model = user_settings.get("selected_model", DEFAULT_MODEL)
    if selected_model not in SUPPORTED_MODELS:
        selected_model = DEFAULT_MODEL

    if chat_message.model_override is not None:
        if chat_message.model_override not in SUPPORTED_MODELS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported model '{chat_message.model_override}'. "
                    f"Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
                ),
            )
        selected_model = chat_message.model_override

    # Step 1: Resolve conversation
    conversation_id, conversation_messages = get_or_create_conversation(
        user_firebase, chat_message.conversation_id, USER_TIMEZONE
    )

    async def event_stream():
        """Generate SSE events for the chat response."""
        try:
            # Send conversation_id first so frontend can track it
            conv_event = {"type": "conversation_id", "conversation_id": conversation_id}
            yield f"data: {json.dumps(conv_event)}\n\n"

            # Step 2: Build messages
            messages = build_message_context(conversation_messages, chat_message.message)

            # Step 3: Tool loop
            from .system_prompts import get_expense_parsing_system_prompt
            user_categories = user_firebase.get_user_categories() if user_firebase else None
            system_prompt = get_expense_parsing_system_prompt(user_categories)

            result = ToolLoopResult()
            async for sse_event in run_claude_tool_loop(
                client, messages, system_prompt,
                os.getenv('ANTHROPIC_API_KEY'), current_user.token, result,
                model=selected_model,
                user_id=current_user.uid,
                firebase_client_instance=user_firebase,
                user_categories=user_categories,
            ):
                yield sse_event

            # Step 4: Save history (skip if tool loop errored)
            if not result.had_error:
                save_conversation_history(
                    user_firebase, conversation_id,
                    chat_message.message,
                    "\n".join(result.final_response_text),
                    result.all_tool_calls,
                    conversation_messages,
                    content_blocks=result.content_blocks or None,
                )

            # Send done signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("Error in chat stream")
            yield f"data: [ERROR] An unexpected error occurred. Please try again.\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ==================== WebSocket: Realtime Voice Assistant ====================

@app.websocket("/ws/realtime")
async def ws_realtime(websocket: WebSocket, mode: str = "voice"):
    """
    WebSocket endpoint for the Watch conversational voice assistant.

    Auth: Firebase token via first WebSocket message.

    First-message auth protocol:
      Watch → Backend: {"type": "auth", "token": "<firebase_id_token>"}
      Backend → Watch: {"type": "auth_ok"} or {"type": "error", ...}

    After auth:
      Watch → Backend: {"type": "audio_chunk", "data": "<base64 pcm16>"}
                       {"type": "audio_done"}
                       {"type": "cancel"}
      Backend → Watch: {"type": "input_transcript",     "text": "..."}
                       {"type": "response_text_delta",  "text": "..."}
                       {"type": "response_audio_delta", "data": "<base64 pcm16>"}
                       {"type": "response_done",        "expense_saved": {...} | null}
                       {"type": "error",                "message": "..."}
    """
    await websocket.accept()

    # Auth: require first-message auth (token must not be sent via query string)
    token = None
    try:
        import asyncio
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_msg = json.loads(raw)
        if auth_msg.get("type") == "auth" and auth_msg.get("token"):
            token = auth_msg["token"]
        else:
            await websocket.send_text(json.dumps({"type": "error", "message": "Expected auth message"}))
            await websocket.close(code=4001)
            return
    except Exception:
            await websocket.send_text(json.dumps({"type": "error", "message": "Auth timeout or invalid message"}))
            await websocket.close(code=4001)
            return

    try:
        import firebase_admin.auth as firebase_auth_mod
        decoded = firebase_auth_mod.verify_id_token(token)
        from .auth import AuthenticatedUser
        user = AuthenticatedUser(
            uid=decoded["uid"],
            email=decoded.get("email"),
            token=token,
        )
    except Exception as exc:
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid token"}))
        await websocket.close(code=4001)
        return

    # Notify client that auth succeeded (for first-message auth flow)
    try:
        await websocket.send_text(json.dumps({"type": "auth_ok"}))
    except Exception:
        return

    if not _mcp_client:
        await websocket.send_text(json.dumps({"type": "error", "message": "MCP backend not ready"}))
        await websocket.close(code=1011)
        return

    # Fetch user categories for dynamic tool schemas
    try:
        user_firebase = FirebaseClient.for_user(user.uid)
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()
        user_categories = user_firebase.get_user_categories()
    except Exception:
        user_categories = None

    # Run the relay session
    try:
        from .realtime_relay import handle_realtime_session
        await handle_realtime_session(websocket, user, _mcp_client, user_categories, mode=mode)
    except WebSocketDisconnect:
        logger.info("Watch WS disconnected: uid=%s", user.uid)
    except Exception as exc:
        logger.exception("Realtime session error: uid=%s", user.uid)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": "An unexpected error occurred"}))
        except Exception:
            pass
