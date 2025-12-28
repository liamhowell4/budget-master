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
from datetime import datetime
from typing import Optional, List
import pytz

from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Header
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .twilio_handler import TwilioHandler
from .firebase_client import FirebaseClient
from .budget_manager import BudgetManager
from .expense_parser import parse_receipt
from .output_schemas import ExpenseType

# Initialize FastAPI app
app = FastAPI(
    title="Personal Expense Tracker API",
    description="API for tracking personal expenses via SMS/MMS and Streamlit UI",
    version="2.0.0"
)

# Add CORS middleware to allow Streamlit (localhost:8501) to call API (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit default port
        "http://127.0.0.1:8501",
        "http://localhost:8000",  # Allow same-origin too
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

def get_twilio_handler():
    """Get or create Twilio handler instance (lazy initialization)."""
    global _twilio_handler
    if _twilio_handler is None:
        _twilio_handler = TwilioHandler()
    return _twilio_handler

# Get user timezone
USER_TIMEZONE = pytz.timezone(os.getenv("USER_TIMEZONE", "America/Chicago"))


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

        # Parse expense
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
            "GET /health"
        ]
    }
