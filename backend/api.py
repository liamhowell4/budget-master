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
from datetime import datetime, date
from typing import Optional, List
import pytz
import base64
import traceback
import json

from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .firebase_client import FirebaseClient
from .budget_manager import BudgetManager
from .output_schemas import ExpenseType, Date
from .recurring_manager import RecurringManager

# Initialize FastAPI app
app = FastAPI(
    title="Personal Expense Tracker API",
    description="API for tracking personal expenses via SMS/MMS and Streamlit UI",
    version="2.0.0"
)

# Add CORS middleware to allow Streamlit (localhost:8501) and MCP Chat Frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # MCP Chat Frontend
        "http://127.0.0.1:3000",
        "http://localhost:8501",   # Streamlit default port
        "http://127.0.0.1:8501",
        "http://localhost:8000",   # Allow same-origin too
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase client and budget manager
firebase_client = FirebaseClient()
budget_manager = BudgetManager(firebase_client)

# MCP Client (initialized on startup)
_mcp_client = None

# Get user timezone
USER_TIMEZONE = pytz.timezone(os.getenv("USER_TIMEZONE", "America/Chicago"))


# ==================== Shared MCP Processing Function ====================

async def process_expense_with_mcp(text: str, image_base64: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """
    Shared MCP processing function for expense parsing.

    Handles text and/or image inputs, processes them via MCP client,
    and returns structured expense data.

    Args:
        text: Text description of expense (can be empty if image provided)
        image_base64: Optional base64-encoded image with data URL prefix
        user_id: Session ID for conversation tracking

    Returns:
        dict with keys: success, expense_id, expense_name, amount, category,
        budget_warning, message

    Raises:
        RuntimeError: If MCP client is not initialized
    """
    if not _mcp_client:
        raise RuntimeError("MCP client not initialized")

    print(f"🤖 Processing with MCP: user_id='{user_id}', text='{text}', has_image={image_base64 is not None}")

    # Call MCP client
    result = await _mcp_client.process_expense_message(
        text=text or "",  # Ensure text is never None
        image_base64=image_base64,
        user_id=user_id
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

async def _check_recurring_expenses_logic() -> dict:
    """
    Core logic for checking and creating pending expenses from recurring templates.

    Used by both startup event (local dev) and /admin/check-recurring endpoint (production).

    Returns:
        dict with created_count, total_recurring, message, and details
    """
    from .recurring_manager import get_today_in_user_timezone

    # Get all active recurring expenses
    recurring_expenses = firebase_client.get_all_recurring_expenses(active_only=True)

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
            existing_pending = firebase_client.get_pending_by_template(recurring.template_id)

            if existing_pending:
                details.append(f"Skipped {recurring.expense_name} - pending already exists")
                continue

            # Create pending expense
            pending = RecurringManager.create_pending_expense_from_recurring(recurring, trigger_date)
            pending_id = firebase_client.save_pending_expense(pending)

            # Update last_reminded
            firebase_client.update_recurring_expense(
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
        print("⏭️  Skipping startup recurring check (SKIP_STARTUP_RECURRING_CHECK=true)")
        return

    try:
        print("🔄 Checking for due recurring expenses on startup...")
        result = await _check_recurring_expenses_logic()
        print(f"✅ {result['message']}")
        for detail in result.get("details", []):
            print(f"   {detail}")
    except Exception as e:
        print(f"❌ Error checking recurring expenses: {e}")
        traceback.print_exc()


@app.on_event("startup")
async def startup_mcp():
    """
    Initialize MCP client on startup.

    This spawns the expense_server.py subprocess and connects via stdio.
    """
    global _mcp_client

    try:
        print("🔄 Initializing MCP client...")
        from .mcp.client import ExpenseMCPClient

        _mcp_client = ExpenseMCPClient()
        await _mcp_client.startup()
        print("✅ MCP backend ready")
    except Exception as e:
        print(f"❌ Error initializing MCP backend: {e}")
        traceback.print_exc()


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
async def mcp_process_expense(
    text: Optional[str] = Form(None, description="Text description of expense"),
    image: Optional[UploadFile] = File(None, description="Receipt image"),
    audio: Optional[UploadFile] = File(None, description="Voice recording for transcription"),
    user_id: Optional[str] = Form(None, description="User/session ID for conversation tracking")
):
    """
    Process expenses via MCP backend.

    Accepts text, image, and/or audio inputs and processes them via Claude + MCP.

    Args:
        text: Optional text description of expense
        image: Optional receipt image file
        audio: Optional voice recording (WAV, MP3, etc.) for Whisper transcription
        user_id: Optional user/session ID for conversation tracking

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
                print(f"⚠️ Audio type {audio.content_type} not in allowed list, proceeding anyway")

            audio_bytes = await audio.read()
            print(f"🎤 Transcribing audio: {len(audio_bytes)} bytes, type: {audio.content_type}")

            transcription = await transcribe_audio(audio_bytes, audio.filename or "recording.wav")
            print(f"📝 Transcription: {transcription}")

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

            # Convert to base64 with data URL prefix
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            # Use the image content type from upload
            image_base64 = f"data:{image.content_type};base64,{image_base64}"

            print(f"📸 Image uploaded: {len(image_bytes)} bytes, type: {image.content_type}")

        # Call shared MCP processing function
        result = await process_expense_with_mcp(
            text=text or "",
            image_base64=image_base64,
            user_id=user_id
        )

        # Return as structured JSON response
        return ExpenseResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            expense_id=result.get("expense_id"),
            expense_name=result.get("expense_name"),
            amount=result.get("amount"),
            category=result.get("category"),
            budget_warning=result.get("budget_warning")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /mcp/process_expense: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/expenses")
async def get_expenses(
    year: Optional[int] = None,
    month: Optional[int] = None,
    category: Optional[str] = None
):
    """
    Get expense history with optional filters.

    Query Parameters:
    - year: Filter by year (e.g., 2025)
    - month: Filter by month (1-12)
    - category: Filter by category (e.g., "FOOD_OUT")

    Returns list of expenses matching filters.
    """
    try:
        # Default to current month if not specified
        if year is None or month is None:
            now = datetime.now(USER_TIMEZONE)
            year = year or now.year
            month = month or now.month

        # Validate category if provided
        category_enum = None
        if category:
            try:
                category_enum = ExpenseType[category.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category. Valid categories: {[e.name for e in ExpenseType]}"
                )

        # Get expenses from Firebase
        expenses = firebase_client.get_monthly_expenses(year, month, category_enum)

        return {
            "year": year,
            "month": month,
            "category": category,
            "count": len(expenses),
            "expenses": expenses
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /expenses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """
    Get current budget status for all categories.

    Query Parameters:
    - year: Year to check (defaults to current year)
    - month: Month to check (defaults to current month)

    Returns budget data for all categories with spending/cap/percentage.
    """
    try:
        # Default to current month
        if year is None or month is None:
            now = datetime.now(USER_TIMEZONE)
            year = year or now.year
            month = month or now.month

        month_name = datetime(year, month, 1).strftime("%B %Y")

        # Get category emoji mapping
        categories_data = firebase_client.get_category_data()
        emoji_map = {cat["category_id"]: cat.get("emoji", "📦") for cat in categories_data}

        # Build category list
        category_list = []

        for expense_type in ExpenseType:
            spending = budget_manager.calculate_monthly_spending(expense_type, year, month)
            cap = firebase_client.get_budget_cap(expense_type.name)

            if cap is None or cap == 0:
                cap = 0
                percentage = 0
                remaining = 0
            else:
                percentage = (spending / cap) * 100 if cap > 0 else 0
                remaining = cap - spending

            category_list.append(BudgetCategory(
                category=expense_type.name,
                spending=spending,
                cap=cap,
                percentage=percentage,
                remaining=remaining,
                emoji=emoji_map.get(expense_type.name, "📦")
            ))

        # Get total budget
        total_spending = budget_manager.calculate_total_monthly_spending(year, month)
        total_cap = firebase_client.get_budget_cap("TOTAL") or 0
        total_percentage = (total_spending / total_cap) * 100 if total_cap > 0 else 0
        total_remaining = total_cap - total_spending

        return BudgetStatusResponse(
            year=year,
            month=month,
            month_name=month_name,
            categories=category_list,
            total_spending=total_spending,
            total_cap=total_cap,
            total_percentage=total_percentage,
            total_remaining=total_remaining
        )

    except Exception as e:
        print(f"Error in /budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/budget-caps/bulk-update", response_model=BulkBudgetUpdateResponse)
async def bulk_update_budget_caps(request: BulkBudgetUpdateRequest):
    """
    Bulk update all budget caps.

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

    Updates all budget caps in budget_caps/ collection atomically.
    """
    try:
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

        # Update total budget cap
        firebase_client.set_budget_cap("TOTAL", request.total_budget)

        # Update all category budget caps
        for category, amount in request.category_budgets.items():
            firebase_client.set_budget_cap(category, amount)

        # Return updated caps
        all_caps = firebase_client.get_all_budget_caps()

        return BulkBudgetUpdateResponse(
            success=True,
            message=f"Successfully updated {len(request.category_budgets)} category budgets and total budget",
            updated_caps=all_caps
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error in /budget-caps/bulk-update: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recurring")
async def get_recurring_expenses():
    """Get all recurring expense templates."""
    try:
        recurring_expenses = firebase_client.get_all_recurring_expenses(active_only=False)

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
        print(f"Error in /recurring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pending")
async def get_pending_expenses():
    """Get all pending expenses awaiting confirmation."""
    try:
        pending_expenses = firebase_client.get_all_pending_expenses(awaiting_only=True)
        return {"pending_expenses": pending_expenses}
    except Exception as e:
        print(f"Error in /pending: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pending/{pending_id}/confirm")
async def confirm_pending_expense(pending_id: str, adjusted_amount: Optional[float] = None):
    """Confirm a pending expense and save it as a regular expense."""
    try:
        # Get pending expense
        pending = firebase_client.get_pending_expense(pending_id)
        if not pending:
            raise HTTPException(status_code=404, detail="Pending expense not found")

        # Convert to expense
        expense = RecurringManager.pending_to_expense(pending, adjusted_amount)

        # Save expense
        doc_id = firebase_client.save_expense(expense, input_type="recurring")

        # Update recurring template's last_user_action
        today = date.today()
        today_date = Date(day=today.day, month=today.month, year=today.year)

        pending_dict = firebase_client.get_all_pending_expenses(awaiting_only=False)
        template_id = None
        for p in pending_dict:
            if p.get("pending_id") == pending_id:
                template_id = p.get("template_id")
                break

        if template_id:
            firebase_client.update_recurring_expense(
                template_id,
                {"last_user_action": {
                    "day": today_date.day,
                    "month": today_date.month,
                    "year": today_date.year
                }}
            )

        # Delete pending expense
        firebase_client.delete_pending_expense(pending_id)

        return {"success": True, "expense_id": doc_id, "message": "Expense confirmed"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /pending/{pending_id}/confirm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/pending/{pending_id}")
async def delete_pending_expense(pending_id: str):
    """Skip/delete a pending expense."""
    try:
        # Get pending to find template_id
        pending_dict = firebase_client.get_all_pending_expenses(awaiting_only=False)
        template_id = None
        for p in pending_dict:
            if p.get("pending_id") == pending_id:
                template_id = p.get("template_id")
                break

        if template_id:
            # Update last_user_action
            today = date.today()
            today_date = Date(day=today.day, month=today.month, year=today.year)
            firebase_client.update_recurring_expense(
                template_id,
                {"last_user_action": {
                    "day": today_date.day,
                    "month": today_date.month,
                    "year": today_date.year
                }}
            )

        # Delete pending expense
        firebase_client.delete_pending_expense(pending_id)

        return {"success": True, "message": "Pending expense deleted"}
    except Exception as e:
        print(f"Error in /pending/{pending_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/recurring/{template_id}")
async def delete_recurring_template(template_id: str):
    """Delete/deactivate a recurring expense template."""
    try:
        firebase_client.delete_recurring_expense(template_id)
        return {"success": True, "message": "Recurring expense deleted"}
    except Exception as e:
        print(f"Error in /recurring/{template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Admin Endpoints ====================

# Load admin API key from environment
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


@app.post("/admin/check-recurring")
async def admin_check_recurring(x_api_key: Optional[str] = Header(None)):
    """
    Check for due recurring expenses and create pending expenses.

    This endpoint is designed to be called by Cloud Scheduler daily.
    Requires ADMIN_API_KEY header for authentication.

    Headers:
        X-API-Key: The admin API key (must match ADMIN_API_KEY env var)

    Returns:
        JSON with created_count and details
    """
    # Verify API key
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_API_KEY not configured on server"
        )

    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-API-Key header"
        )

    try:
        print("🔄 [Admin] Checking for due recurring expenses...")
        result = await _check_recurring_expenses_logic()
        print(f"✅ [Admin] {result['message']}")
        return result
    except Exception as e:
        print(f"❌ [Admin] Error checking recurring expenses: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "endpoints": [
            "POST /mcp/process_expense",
            "GET /expenses",
            "GET /budget",
            "PUT /budget-caps/bulk-update",
            "GET /recurring",
            "GET /pending",
            "POST /pending/{id}/confirm",
            "DELETE /pending/{id}",
            "DELETE /recurring/{id}",
            "POST /admin/check-recurring",
            "GET /health",
            "GET /servers",
            "POST /connect/{server_id}",
            "GET /status",
            "POST /disconnect",
            "POST /chat/stream"
        ]
    }


# ==================== MCP Chat Frontend Endpoints ====================

@app.get("/servers")
async def list_servers():
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
            "path": server.path,
            "description": server.description
        }
        for server in servers
    ]


@app.post("/connect/{server_id}")
async def connect_to_server(server_id: str):
    """
    Connect to a specific MCP server.

    Disconnects from current server (if any) and establishes connection
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
async def get_connection_status():
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
async def disconnect_from_server():
    """
    Disconnect from current MCP server.

    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.connection_manager import get_connection_manager

    conn_manager = get_connection_manager()

    # Disconnect
    await conn_manager.disconnect()

    return {"success": True}


class ChatMessage(BaseModel):
    """Request model for chat messages."""
    message: str


@app.post("/chat/stream")
async def chat_stream(chat_message: ChatMessage):
    """
    Process a chat message and stream response with tool calls.

    Uses Server-Sent Events (SSE) to stream:
    - tool_start events when tools begin execution
    - tool_end events when tools finish
    - text events for response chunks
    - [DONE] signal when complete
    - [ERROR] signal on errors

    Follows BACKEND_API_CONTRACT.md specification.
    """
    from .mcp.connection_manager import get_connection_manager
    from anthropic import Anthropic

    conn_manager = get_connection_manager()

    # Check if connected
    if not conn_manager.is_connected:
        async def error_stream():
            yield "data: [ERROR] Not connected to any server. Use POST /connect/{server_id} first.\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Get client and tools
    client = conn_manager.get_client()
    if not client or not client.session:
        async def error_stream():
            yield "data: [ERROR] MCP client not initialized\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_stream():
        """Generate SSE events for the chat response."""
        try:
            # Get available tools from MCP server
            response = await client.session.list_tools()
            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in response.tools]

            # Get system prompt
            from .system_prompts import get_expense_parsing_system_prompt
            system_prompt = get_expense_parsing_system_prompt()

            # Build message
            messages = [{
                "role": "user",
                "content": chat_message.message
            }]

            # Call Claude API with tools
            anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            api_response = anthropic_client.messages.create(
                model="claude-sonnet-4-5",
                system=system_prompt,
                max_tokens=2000,
                messages=messages,
                tools=available_tools
            )

            # Process response and handle tool calls in a loop
            while api_response.stop_reason == "tool_use":
                # Collect all tool uses and text from this response
                assistant_content = []
                tool_results = []

                for content in api_response.content:
                    if content.type == 'text':
                        # Capture any text that appears during tool use (though we usually don't stream it per contract)
                        assistant_content.append({
                            "type": "text",
                            "text": content.text
                        })
                    elif content.type == 'tool_use':
                        tool_name = content.name
                        tool_args = content.input
                        tool_use_id = content.id

                        # Emit tool_start event
                        tool_start_event = {
                            "type": "tool_start",
                            "id": tool_use_id,
                            "name": tool_name,
                            "args": tool_args
                        }
                        yield f"data: {json.dumps(tool_start_event)}\n\n"

                        # Execute tool call via MCP
                        result = await client.session.call_tool(tool_name, tool_args)

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

                        # Emit tool_end event
                        tool_end_event = {
                            "type": "tool_end",
                            "id": tool_use_id,
                            "name": tool_name
                        }
                        yield f"data: {json.dumps(tool_end_event)}\n\n"

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

                # Get next response from Claude
                api_response = anthropic_client.messages.create(
                    model="claude-sonnet-4-5",
                    system=system_prompt,
                    max_tokens=2000,
                    messages=messages,
                    tools=available_tools
                )

            # Process final response (no more tool calls)
            print(f"🔍 Final response stop_reason: {api_response.stop_reason}")
            print(f"🔍 Final response content count: {len(api_response.content)}")

            for content in api_response.content:
                print(f"🔍 Content type: {content.type}")
                if content.type == 'text':
                    text = content.text
                    print(f"🔍 Text content length: {len(text)}")
                    print(f"🔍 Text preview: {text[:100]}...")

                    # Send entire text as one event (or chunk into reasonable sizes)
                    # API contract allows chunking for smooth streaming
                    if len(text) > 0:
                        # Send text in larger chunks (or all at once)
                        text_event = {
                            "type": "text",
                            "content": text
                        }
                        yield f"data: {json.dumps(text_event)}\n\n"
                    else:
                        print("⚠️ Empty text content!")

            # Send done signal
            print("✅ Sending [DONE] signal")
            yield "data: [DONE]\n\n"

        except Exception as e:
            # Send error signal
            error_msg = f"[ERROR] {str(e)}"
            yield f"data: {error_msg}\n\n"
            traceback.print_exc()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
