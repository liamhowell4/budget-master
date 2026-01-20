"""
FastAPI Backend - Personal Expense Tracker API

Endpoints:
- POST /twilio/webhook - Twilio SMS/MMS webhook handler
- POST /streamlit/process - Streamlit UI expense submission (audio/image/text)
- GET /expenses - Query expense history with filters
- GET /budget - Get current budget status
- GET /health - Health check
"""

import os
from datetime import datetime, date
from typing import Optional, List
import pytz
import requests
import base64
import traceback
import json

from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Header
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .twilio_handler import TwilioHandler
from .firebase_client import FirebaseClient
from .budget_manager import BudgetManager
from .expense_parser import parse_receipt
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

# Lazy initialization for Twilio handler (only when needed)
_twilio_handler = None

# MCP Backend Feature Flag (Phase 4.1)
USE_MCP_BACKEND = os.getenv("USE_MCP_BACKEND", "false").lower() == "true"

# MCP Client (lazy initialization on startup if feature flag enabled)
_mcp_client = None

def get_twilio_handler():
    """Get or create Twilio handler instance (lazy initialization)."""
    global _twilio_handler
    if _twilio_handler is None:
        _twilio_handler = TwilioHandler()
    return _twilio_handler

# Get user timezone
USER_TIMEZONE = pytz.timezone(os.getenv("USER_TIMEZONE", "America/Chicago"))


# ==================== Shared MCP Processing Function ====================

async def process_expense_with_mcp(text: str, image_base64: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """
    Shared MCP processing function for expense parsing.

    This function is called by both /twilio/webhook-mcp and /mcp/process_expense.
    It handles text and/or image inputs, processes them via MCP client,
    and returns structured expense data.

    Args:
        text: Text description of expense (can be empty if image provided)
        image_base64: Optional base64-encoded image with data URL prefix
        user_id: Phone number or session ID for conversation tracking

    Returns:
        dict with keys: success, expense_id, expense_name, amount, category,
        budget_warning, message

    Raises:
        RuntimeError: If MCP client is not initialized
    """
    if not _mcp_client:
        raise RuntimeError("MCP client not initialized. Set USE_MCP_BACKEND=true")

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


# ==================== Startup Events ====================

@app.on_event("startup")
async def check_recurring_expenses():
    """
    Check for due recurring expenses on API startup.

    This runs every time the API starts. It checks all active recurring expenses
    and creates pending expenses if they're due.

    NOTE: This is a temporary implementation for pre-Cloud Functions deployment.
    When deployed to Cloud Functions, this logic will move to a daily Cloud Scheduler
    job that calls /admin/check-recurring endpoint.

    See RECURRING_IMPLEMENTATION_PLAN.md for migration details.
    """
    try:
        print("🔄 Checking for due recurring expenses...")

        # Get all active recurring expenses
        recurring_expenses = firebase_client.get_all_recurring_expenses(active_only=True)

        if not recurring_expenses:
            print("✅ No active recurring expenses found")
            return

        print(f"📋 Found {len(recurring_expenses)} active recurring expenses")

        # Use timezone-aware today (not UTC)
        from .recurring_manager import get_today_in_user_timezone
        today = get_today_in_user_timezone()
        today_date = Date(day=today.day, month=today.month, year=today.year)

        created_count = 0

        for recurring in recurring_expenses:
            # Check if we should create a pending expense
            should_create, trigger_date = RecurringManager.should_create_pending(recurring)

            if should_create and trigger_date:
                # Check if pending already exists for this template
                existing_pending = firebase_client.get_pending_by_template(recurring.template_id)

                if existing_pending:
                    print(f"⏭️  Skipping {recurring.expense_name} - pending already exists")
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
                print(f"✅ Created pending expense for {recurring.expense_name} (due {trigger_date.month}/{trigger_date.day})")

        if created_count > 0:
            print(f"🎉 Created {created_count} pending expense(s)")
        else:
            print("✅ All recurring expenses up to date")

    except Exception as e:
        print(f"❌ Error checking recurring expenses: {e}")
        traceback.print_exc()


@app.on_event("startup")
async def startup_mcp():
    """
    Initialize MCP client if feature flag is enabled.

    This spawns the expense_server.py subprocess and connects via stdio.
    Only runs if USE_MCP_BACKEND=true in environment.
    """
    global _mcp_client

    if USE_MCP_BACKEND:
        try:
            print("🔄 MCP backend enabled - initializing MCP client...")
            from .mcp.client import ExpenseMCPClient

            _mcp_client = ExpenseMCPClient()
            await _mcp_client.startup()
            print("✅ MCP backend ready")
        except Exception as e:
            print(f"❌ Error initializing MCP backend: {e}")
            traceback.print_exc()
            # Don't fail startup - allow OpenAI backend to still work
    else:
        print("ℹ️  MCP backend disabled (USE_MCP_BACKEND=false)")


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

@app.post("/twilio/webhook", response_class=PlainTextResponse)
async def twilio_webhook(request: Request, x_twilio_signature: str = Header(None)):
    """
    Twilio SMS/MMS webhook handler.

    Receives incoming SMS/MMS messages, processes expenses, and responds.
    Validates Twilio signature for security.
    """
    try:
        # Get Twilio handler (lazy initialization)
        handler = get_twilio_handler()

        # Get form data and URL for signature validation
        form_data = await request.form()
        url = str(request.url)

        # Validate Twilio signature
        if x_twilio_signature:
            is_valid = handler.validate_request(
                url=url,
                post_data=dict(form_data),
                signature=x_twilio_signature
            )
            if not is_valid:
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        # Get sender's phone number
        from_number = form_data.get("From", "")

        # Process the webhook and get response message
        response_message = handler.handle_webhook(from_number, dict(form_data))

        # Return plain text response (Twilio will send as SMS)
        return response_message

    except Exception as e:
        print(f"Error in Twilio webhook: {e}")
        return "❌ Error processing your message. Please try again."


@app.post("/twilio/webhook-mcp", response_class=PlainTextResponse)
async def twilio_webhook_mcp(request: Request, x_twilio_signature: str = Header(None)):
    """
    Twilio SMS/MMS webhook handler using MCP backend.

    This endpoint uses Claude + MCP architecture instead of OpenAI.
    Maintains same signature validation and response format as /twilio/webhook.

    Only active if USE_MCP_BACKEND=true in environment.
    """
    try:
        # Check if MCP backend is enabled
        if not USE_MCP_BACKEND or not _mcp_client:
            return "❌ MCP backend not enabled. Please use /twilio/webhook endpoint."

        # Get Twilio handler for signature validation and image download
        handler = get_twilio_handler()

        # Get form data and URL for signature validation
        form_data = await request.form()
        url = str(request.url)

        # Validate Twilio signature
        if x_twilio_signature:
            is_valid = handler.validate_request(
                url=url,
                post_data=dict(form_data),
                signature=x_twilio_signature
            )
            if not is_valid:
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        # Get message body and phone number
        message_body = form_data.get("Body", "").strip()
        from_number = form_data.get("From", "")  # Phone number for conversation tracking

        # Check for images (MMS)
        num_media = int(form_data.get("NumMedia", 0))
        image_base64 = None

        if num_media > 0:
            # Download first image and convert to base64
            media_url = form_data.get("MediaUrl0")
            media_type = form_data.get("MediaContentType0", "image/jpeg")

            if media_url:
                print(f"📸 Downloading image from: {media_url}")
                response = requests.get(media_url, auth=(
                    os.getenv("TWILIO_ACCOUNT_SID"),
                    os.getenv("TWILIO_ACCOUNT_TOKEN")
                ))

                if response.status_code == 200:
                    # Convert to base64
                    image_bytes = response.content
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    # Add data URL prefix
                    image_base64 = f"data:{media_type};base64,{image_base64}"
                    print(f"✅ Image downloaded and encoded ({len(image_bytes)} bytes)")

        # Process with shared MCP function
        result = await process_expense_with_mcp(
            text=message_body,
            image_base64=image_base64,
            user_id=from_number  # Pass phone number for conversation tracking
        )

        # Get response message (already formatted by shared function)
        response_message = result.get("message", "❌ Error processing expense")

        print(f"📤 Sending response: {response_message}")
        return response_message

    except Exception as e:
        print(f"Error in MCP Twilio webhook: {e}")
        traceback.print_exc()
        return "❌ Error processing your message. Please try again."


@app.post("/mcp/process_expense", response_model=ExpenseResponse)
async def mcp_process_expense(
    text: Optional[str] = Form(None, description="Text description of expense"),
    image: Optional[UploadFile] = File(None, description="Receipt image"),
    user_id: Optional[str] = Form(None, description="User/session ID for conversation tracking")
):
    """
    Generic MCP endpoint for processing expenses.

    This endpoint is used by Streamlit and can be used by other clients.
    It accepts text and/or image inputs and processes them via MCP backend.

    Args:
        text: Optional text description of expense
        image: Optional receipt image file
        user_id: Optional user/session ID for conversation tracking

    Returns:
        ExpenseResponse with structured expense data

    Note: This endpoint requires USE_MCP_BACKEND=true to be set.
    """
    try:
        # Check if MCP backend is enabled
        if not USE_MCP_BACKEND or not _mcp_client:
            raise HTTPException(
                status_code=503,
                detail="MCP backend not enabled. Set USE_MCP_BACKEND=true"
            )

        # Must have at least one input
        if not text and not image:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least one input: text or image"
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


@app.post("/streamlit/process", response_model=ExpenseResponse)
async def streamlit_process(
    audio: Optional[UploadFile] = File(None, description="Audio file for transcription"),
    image: Optional[UploadFile] = File(None, description="Receipt image"),
    text: Optional[str] = Form(None, description="Text description of expense")
):
    """
    Process expense from Streamlit UI.

    Accepts:
    - Audio file (for Whisper transcription)
    - Receipt image
    - Text description
    - Any combination of the above
    - Commands: "status", "total"

    Returns expense data and budget warning, or command response.
    """
    try:
        # Must have at least one input
        if not audio and not image and not text:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least one input: audio, image, or text"
            )

        # Check for command keywords (status, total) - only if text-only (no images/audio)
        if text and not image and not audio:
            text_lower = text.lower().strip()
            if text_lower in ["status", "total", "summary"]:
                twilio_handler = get_twilio_handler()
                if text_lower in ["status", "summary"]:
                    response_message = twilio_handler.handle_status_command()
                else:  # total
                    response_message = twilio_handler.handle_total_command()

                return ExpenseResponse(
                    success=True,
                    message=response_message,
                    expense_id=None,
                    expense_name=None,
                    amount=None,
                    category=None,
                    budget_warning=None
                )

        # Process audio if provided (TODO: Implement Whisper transcription in Phase 4)
        transcription = None
        if audio:
            # For now, return error - will implement in Phase 4
            raise HTTPException(
                status_code=501,
                detail="Audio transcription not yet implemented. Coming in Phase 4!"
            )

        # Process image
        image_bytes = None
        if image:
            # Validate image type
            allowed_types = ["image/jpeg", "image/jpg", "image/png"]
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image type. Allowed: {allowed_types}"
                )
            image_bytes = await image.read()

        # Combine text and transcription
        text_input = None
        if text:
            text_input = text
        elif transcription:
            text_input = transcription

        # Check if this is a recurring expense (text-only, no images)
        if text_input and not image_bytes:
            from .expense_parser import detect_recurring

            print(f"\n🔍 Checking if text is recurring (Streamlit)...")
            print(f"   Text: '{text_input}'")

            detection = detect_recurring(text_input)

            print(f"   is_recurring: {detection.is_recurring}")
            print(f"   confidence: {detection.confidence}")
            print(f"   explanation: {detection.explanation}")

            if detection.is_recurring and detection.recurring_expense:
                print(f"   ✅ Detected as recurring! Creating recurring expense...")

                # Save recurring expense template
                recurring = detection.recurring_expense
                template_id = firebase_client.save_recurring_expense(recurring)

                print(f"   ✅ Created recurring template: {template_id}")

                # Check if we should create a pending expense retroactively
                recurring.template_id = template_id
                should_create, trigger_date = RecurringManager.should_create_pending(recurring)

                if trigger_date:
                    today = date.today()
                    if trigger_date <= today:
                        # Create pending expense
                        pending = RecurringManager.create_pending_expense_from_recurring(recurring, trigger_date)
                        pending_id = firebase_client.save_pending_expense(pending)

                        # Update last_reminded
                        today_date = Date(day=today.day, month=today.month, year=today.year)
                        firebase_client.update_recurring_expense(
                            template_id,
                            {"last_reminded": {
                                "day": today_date.day,
                                "month": today_date.month,
                                "year": today_date.year
                            }}
                        )

                        print(f"   ✅ Created pending expense (retroactive): {pending_id}")

                        response = ExpenseResponse(
                            success=True,
                            message=f"✅ Created recurring {recurring.expense_name} expense. Pending confirmation for {trigger_date.month}/{trigger_date.day}/{trigger_date.year} - check Dashboard!",
                            expense_id=template_id,
                            expense_name=recurring.expense_name,
                            amount=recurring.amount,
                            category=recurring.category.name,
                            budget_warning=None
                        )
                        print(f"   🎯 Returning response with pending expense")
                        return response

                response = ExpenseResponse(
                    success=True,
                    message=f"✅ Created recurring {recurring.expense_name} expense (${recurring.amount:.2f} {recurring.frequency.value})",
                    expense_id=template_id,
                    expense_name=recurring.expense_name,
                    amount=recurring.amount,
                    category=recurring.category.name,
                    budget_warning=None
                )
                print(f"   🎯 Returning response (future date)")
                return response
            else:
                print(f"   ℹ️  Not recurring (confidence too low or no parsed expense)")

        # Parse expense (regular, one-time expense)
        expense = parse_receipt(
            image_bytes=image_bytes,
            text=text_input,
            context=None
        )

        # Validate amount
        if expense.amount == 0:
            return ExpenseResponse(
                success=False,
                message="Couldn't find an amount. Please provide a complete expense with an amount.",
                expense_id=None
            )

        # Get current date
        now = datetime.now(USER_TIMEZONE)
        year, month = now.year, now.month

        # Get budget warning BEFORE saving
        warning = budget_manager.get_budget_warning(
            category=expense.category,
            amount=expense.amount,
            year=year,
            month=month
        )

        # Save to Firestore (with retry)
        saved = False
        doc_id = None
        for attempt in range(2):
            try:
                doc_id = firebase_client.save_expense(expense, input_type="streamlit")
                saved = True
                break
            except Exception as e:
                if attempt == 0:
                    print(f"Retry saving expense: {e}")
                    continue
                else:
                    raise

        if not saved:
            return ExpenseResponse(
                success=False,
                message="Failed to save expense after retry. Please try again.",
                expense_id=None
            )

        # Return success response
        return ExpenseResponse(
            success=True,
            message=f"Saved ${expense.amount:.2f} {expense.expense_name}",
            expense_id=doc_id,
            expense_name=expense.expense_name,
            amount=expense.amount,
            category=expense.category.name,
            budget_warning=warning if warning else None
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /streamlit/process: {e}")
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "endpoints": [
            "POST /twilio/webhook",
            "POST /streamlit/process",
            "GET /expenses",
            "GET /budget",
            "GET /recurring",
            "GET /pending",
            "POST /pending/{id}/confirm",
            "DELETE /pending/{id}",
            "DELETE /recurring/{id}",
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
