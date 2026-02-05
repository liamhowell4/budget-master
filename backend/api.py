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

from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of backend/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)

from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .firebase_client import FirebaseClient
from .budget_manager import BudgetManager
from .output_schemas import ExpenseType, Date, CategoryCreate, CategoryUpdate, CategoryReorder
from .recurring_manager import RecurringManager
from .auth import get_current_user, get_optional_user, AuthenticatedUser
from .category_defaults import DEFAULT_CATEGORIES, MAX_CATEGORIES

# Initialize FastAPI app
app = FastAPI(
    title="Personal Expense Tracker API",
    description="API for tracking personal expenses via SMS/MMS and Streamlit UI",
    version="2.0.0"
)

# Add CORS middleware to allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React Frontend (local)
        "http://127.0.0.1:3000",
        "http://localhost:3001",   # React Frontend (alt port)
        "http://127.0.0.1:3001",
        "http://localhost:8501",   # Streamlit default port
        "http://127.0.0.1:8501",
        "http://localhost:8000",   # Allow same-origin too
        "http://127.0.0.1:8000",
        "https://budget-master-lh.web.app",      # Firebase Hosting (production)
        "https://budget-master-lh.firebaseapp.com",  # Firebase Hosting (alt domain)
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

async def process_expense_with_mcp(
    text: str,
    image_base64: Optional[str] = None,
    user_id: str = None,
    auth_token: str = None,
    conversation_id: Optional[str] = None
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

    print(f"🤖 Processing with MCP: user_id='{user_id}', text='{text}', has_image={image_base64 is not None}, conversation_id={conversation_id}")

    # Call MCP client - pass auth_token for MCP server verification
    result = await _mcp_client.process_expense_message(
        text=text or "",  # Ensure text is never None
        image_base64=image_base64,
        auth_token=auth_token,
        user_id=user_id,
        conversation_id=conversation_id
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
    Also pre-connects the ConnectionManager so frontend connections are instant.
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

    # Pre-connect the ConnectionManager so frontend doesn't wait
    try:
        print("🔄 Pre-connecting MCP server for frontend...")
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
                print(f"✅ MCP server pre-connected ({len(tools)} tools available)")
            else:
                print(f"⚠️ MCP pre-connection failed: {error}")
    except Exception as e:
        print(f"⚠️ MCP pre-connection error (non-fatal): {e}")


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
        # Pass auth_token for MCP server verification (defense in depth)
        result = await process_expense_with_mcp(
            text=text or "",
            image_base64=image_base64,
            user_id=current_user.uid,
            auth_token=current_user.token,
            conversation_id=conversation_id
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
        print(f"Error in /mcp/process_expense: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/expenses")
async def get_expenses(
    current_user: AuthenticatedUser = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None,
    category: Optional[str] = None
):
    """
    Get expense history with optional filters.

    Requires authentication via Firebase Auth token.

    Query Parameters:
    - year: Filter by year (e.g., 2025)
    - month: Filter by month (1-12)
    - category: Filter by category (e.g., "FOOD_OUT")

    Returns list of expenses matching filters.
    """
    try:
        # Create user-scoped Firebase client
        user_firebase = FirebaseClient.for_user(current_user.uid)

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

        # Get expenses from Firebase (user-scoped)
        expenses = user_firebase.get_monthly_expenses(year, month, category_enum)

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
        deleted = user_firebase.delete_expense(expense_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Expense not found")

        return {"success": True, "expense_id": expense_id}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in DELETE /expenses/{expense_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExpenseUpdateRequest(BaseModel):
    """Request body for updating an expense."""
    expense_name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None


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

        # Update the expense
        updated = user_firebase.update_expense(
            expense_id=expense_id,
            expense_name=update_data.expense_name,
            amount=update_data.amount,
            category_str=update_data.category
        )

        if not updated:
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
        print(f"Error in PUT /expenses/{expense_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """
    Get current budget status for all categories.

    Requires authentication via Firebase Auth token.

    Query Parameters:
    - year: Year to check (defaults to current year)
    - month: Month to check (defaults to current month)

    Returns budget data for all categories with spending/cap/percentage.
    Total spending excludes categories marked with exclude_from_total=true.
    """
    try:
        # Create user-scoped Firebase client and budget manager
        user_firebase = FirebaseClient.for_user(current_user.uid)
        user_budget_manager = BudgetManager(user_firebase)

        # Default to current month
        if year is None or month is None:
            now = datetime.now(USER_TIMEZONE)
            year = year or now.year
            month = month or now.month

        month_name = datetime(year, month, 1).strftime("%B %Y")

        # Silent migration if needed
        if not user_firebase.has_categories_setup():
            user_firebase.migrate_from_budget_caps()

        # Get user's custom categories
        user_categories = user_firebase.get_user_categories()

        # Build a map of category_id -> category data for quick lookup
        category_map = {cat["category_id"]: cat for cat in user_categories}

        # Get spending by category for the month
        from .output_schemas import Date as DateModel
        start_date = DateModel(day=1, month=month, year=year)
        # Get last day of month
        if month == 12:
            end_day = 31
        else:
            from calendar import monthrange
            end_day = monthrange(year, month)[1]
        end_date = DateModel(day=end_day, month=month, year=year)

        spending_by_category = user_firebase.get_spending_by_category(start_date, end_date)

        # Build category list and track excluded categories
        category_list = []
        excluded_categories = []
        total_spending_filtered = 0.0
        excluded_cap_total = 0.0

        for cat in user_categories:
            category_id = cat["category_id"]
            spending = spending_by_category.get(category_id, 0)
            cap = cat.get("monthly_cap", 0)
            is_excluded = cat.get("exclude_from_total", False)

            if cap > 0:
                percentage = (spending / cap) * 100
                remaining = cap - spending
            else:
                percentage = 0
                remaining = 0

            category_list.append(BudgetCategory(
                category=category_id,
                spending=spending,
                cap=cap,
                percentage=percentage,
                remaining=remaining,
                emoji=cat.get("icon", "📦")  # Use icon as emoji for backwards compatibility
            ))

            # Track excluded categories and calculate filtered totals
            if is_excluded:
                excluded_categories.append(category_id)
                excluded_cap_total += cap
            else:
                total_spending_filtered += spending

        # Get total budget cap and subtract excluded category caps
        total_cap_raw = user_firebase.get_total_monthly_budget() or 0
        total_cap = total_cap_raw - excluded_cap_total
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
            excluded_categories=excluded_categories
        )

    except Exception as e:
        print(f"Error in /budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in /budget-caps/bulk-update: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in GET /categories: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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

        # Check available budget
        total_budget = user_firebase.get_total_monthly_budget()
        categories = user_firebase.get_user_categories()
        allocated = sum(cat.get("monthly_cap", 0) for cat in categories)
        available = total_budget - allocated

        if category.monthly_cap > available:
            raise HTTPException(
                status_code=400,
                detail=f"Monthly cap ${category.monthly_cap:.2f} exceeds available budget ${available:.2f}"
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
        print(f"Error in POST /categories: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in PUT /categories/reorder: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        success = user_firebase.update_category(category_id, update_dict)

        if not success:
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
        print(f"Error in PUT /categories/{category_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in DELETE /categories/{category_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in GET /budget/total: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in PUT /budget/total: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in /recurring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in /pending: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        today = date.today()
        today_date = Date(day=today.day, month=today.month, year=today.year)

        pending_dict = user_firebase.get_all_pending_expenses(awaiting_only=False)
        template_id = None
        for p in pending_dict:
            if p.get("pending_id") == pending_id:
                template_id = p.get("template_id")
                break

        if template_id:
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

        return {"success": True, "expense_id": doc_id, "message": "Expense confirmed"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /pending/{pending_id}/confirm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in /pending/{pending_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in /recurring/{template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            if conv.get("created_at"):
                created = conv["created_at"]
                if hasattr(created, 'isoformat'):
                    conv["created_at"] = created.isoformat()
            if conv.get("last_activity"):
                last = conv["last_activity"]
                if hasattr(last, 'isoformat'):
                    conv["last_activity"] = last.isoformat()

        return {"conversations": conversations}
    except Exception as e:
        print(f"Error in /conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        if conversation.get("created_at"):
            created = conversation["created_at"]
            if hasattr(created, 'isoformat'):
                conversation["created_at"] = created.isoformat()
        if conversation.get("last_activity"):
            last = conversation["last_activity"]
            if hasattr(last, 'isoformat'):
                conversation["last_activity"] = last.isoformat()

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /conversations/{conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a specific conversation. Requires authentication."""
    try:
        user_firebase = FirebaseClient.for_user(current_user.uid)
        deleted = user_firebase.delete_conversation(conversation_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /conversations/{conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"Error in POST /conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Admin Endpoints ====================

# Load admin API key from environment
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


@app.post("/admin/check-recurring")
async def admin_check_recurring(x_api_key: Optional[str] = Header(None)):
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

    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-API-Key header"
        )

    try:
        print("🔄 [Admin] Checking for due recurring expenses for all users...")

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
            print(f"  Checking user: {user_id}")

            user_firebase = FirebaseClient.for_user(user_id)
            result = await _check_recurring_expenses_logic(user_firebase)

            total_created += result.get("created_count", 0)
            if result.get("details"):
                all_details.extend([f"[{user_id}] {d}" for d in result["details"]])

        message = f"Checked {users_checked} user(s), created {total_created} pending expense(s)"
        print(f"✅ [Admin] {message}")

        return {
            "created_count": total_created,
            "users_checked": users_checked,
            "message": message,
            "details": all_details
        }
    except Exception as e:
        print(f"[Admin] Error checking recurring expenses: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/cleanup-conversations")
async def admin_cleanup_conversations(
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

    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-API-Key header"
        )

    try:
        print(f"[Admin] Cleaning up conversations older than {ttl_hours} hours...")
        results = FirebaseClient.cleanup_all_users_conversations(ttl_hours=ttl_hours)

        total_deleted = results.pop("_total", 0)
        message = f"Deleted {total_deleted} old conversation(s)"
        print(f"[Admin] {message}")

        return {
            "deleted_count": total_deleted,
            "ttl_hours": ttl_hours,
            "message": message,
            "per_user": results
        }
    except Exception as e:
        print(f"[Admin] Error cleaning up conversations: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "3.2.0",
        "endpoints": [
            "POST /mcp/process_expense",
            "GET /expenses",
            "GET /budget",
            "PUT /budget-caps/bulk-update",
            "GET /categories",
            "POST /categories",
            "PUT /categories/{id}",
            "DELETE /categories/{id}",
            "PUT /categories/reorder",
            "GET /categories/defaults",
            "GET /budget/total",
            "PUT /budget/total",
            "GET /recurring",
            "GET /pending",
            "POST /pending/{id}/confirm",
            "DELETE /pending/{id}",
            "DELETE /recurring/{id}",
            "GET /conversations",
            "GET /conversations/{id}",
            "POST /conversations",
            "DELETE /conversations/{id}",
            "POST /admin/check-recurring",
            "POST /admin/cleanup-conversations",
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
    conversation_id: Optional[str] = None


@app.post("/chat/stream")
async def chat_stream(
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
    from anthropic import Anthropic
    from datetime import timedelta

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

    # Set up user-scoped Firebase client
    user_firebase = FirebaseClient.for_user(current_user.uid)

    # Determine conversation_id (get existing or create new based on 12h inactivity)
    conversation_id = chat_message.conversation_id
    conversation_messages = []

    INACTIVITY_THRESHOLD_HOURS = 12

    if conversation_id:
        # Check if existing conversation is stale (>12 hours idle)
        existing_conv = user_firebase.get_conversation(conversation_id)
        if existing_conv:
            last_activity = existing_conv.get("last_activity")
            if last_activity:
                now = datetime.now(USER_TIMEZONE)

                # Handle Firestore timestamp
                if hasattr(last_activity, 'timestamp'):
                    last_activity = datetime.fromtimestamp(last_activity.timestamp(), USER_TIMEZONE)
                elif isinstance(last_activity, datetime):
                    if last_activity.tzinfo is None:
                        last_activity = USER_TIMEZONE.localize(last_activity)

                if now - last_activity > timedelta(hours=INACTIVITY_THRESHOLD_HOURS):
                    print(f"Conversation {conversation_id} is stale (>{INACTIVITY_THRESHOLD_HOURS}h), creating new one")
                    conversation_id = None
                else:
                    # Get existing messages for context
                    conversation_messages = existing_conv.get("messages", [])
        else:
            conversation_id = None  # Conversation not found

    # Create new conversation if needed
    if not conversation_id:
        conversation_id = user_firebase.create_conversation()

    async def event_stream():
        """Generate SSE events for the chat response."""
        nonlocal conversation_id
        final_response_text = []

        try:
            # Send conversation_id first so frontend can track it
            conv_event = {"type": "conversation_id", "conversation_id": conversation_id}
            yield f"data: {json.dumps(conv_event)}\n\n"

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

            # Build messages with conversation history
            messages = []

            # Add previous conversation messages for context
            for msg in conversation_messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Add current user message
            messages.append({
                "role": "user",
                "content": chat_message.message
            })

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
                        assistant_content.append({
                            "type": "text",
                            "text": content.text
                        })
                    elif content.type == 'tool_use':
                        tool_name = content.name
                        tool_args = content.input
                        tool_use_id = content.id

                        # Inject auth_token for MCP tool authentication (defense in depth)
                        if tool_name != "get_categories":
                            tool_args = {**tool_args, "auth_token": current_user.token}

                        # Emit tool_start event (without auth token for security)
                        tool_start_event = {
                            "type": "tool_start",
                            "id": tool_use_id,
                            "name": tool_name,
                            "args": {k: v for k, v in tool_args.items() if k != "auth_token"}
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

                        # Emit tool_end event with result
                        try:
                            parsed_result = json.loads(result_text)
                        except (json.JSONDecodeError, TypeError):
                            parsed_result = result_text

                        tool_end_event = {
                            "type": "tool_end",
                            "id": tool_use_id,
                            "name": tool_name,
                            "result": parsed_result
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
            for content in api_response.content:
                if content.type == 'text':
                    text = content.text
                    final_response_text.append(text)

                    if len(text) > 0:
                        text_event = {
                            "type": "text",
                            "content": text
                        }
                        yield f"data: {json.dumps(text_event)}\n\n"

            # Save messages to Firestore conversation
            user_firebase.add_message_to_conversation(conversation_id, "user", chat_message.message)
            full_response = "\n".join(final_response_text)
            if full_response:
                user_firebase.add_message_to_conversation(conversation_id, "assistant", full_response)

            # Update conversation summary from first user message
            if len(conversation_messages) == 0:
                # This is the first message, set summary
                summary = chat_message.message[:50]
                if len(chat_message.message) > 50:
                    summary += "..."
                user_firebase.update_conversation_summary(conversation_id, summary)

            # Send done signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"[ERROR] {str(e)}"
            yield f"data: {error_msg}\n\n"
            traceback.print_exc()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
