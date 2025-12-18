import json
from pathlib import Path
import re

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from expense_parser import parse_receipt
from output_schemas import Expense

app = FastAPI(
    title="Expense Receipt Parser API",
    description="API for parsing receipt images into structured expense data",
    version="1.0.0"
)


def sanitize_filename(name: str) -> str:
    """Convert expense name to a valid filename."""
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[\s]+', '_', sanitized)
    return sanitized.lower()[:50]


def save_expense(expense: Expense) -> str:
    """Save expense to JSON file in outputs folder."""
    outputs_dir = Path(__file__).parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    filename = sanitize_filename(expense.expense_name)
    filepath = outputs_dir / f"{filename}.json"
    
    # Handle duplicate filenames by adding a number
    counter = 1
    while filepath.exists():
        filepath = outputs_dir / f"{filename}_{counter}.json"
        counter += 1
    
    with open(filepath, 'w') as f:
        json.dump(expense.model_dump(), f, indent=2, default=str)
    
    return str(filepath)


@app.post("/parse-receipt", response_model=dict)
async def parse_receipt_endpoint(
    image: UploadFile = File(..., description="Receipt image file"),
    context: str = Form("", description="Additional context (category, participants, project)")
):
    """
    Parse a receipt image and extract expense data.
    
    - **image**: Receipt image file (jpg, jpeg, png)
    - **context**: Additional context like expense category, participants, project name
    
    Returns the parsed Expense data and the path where it was saved.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {allowed_types}"
        )
    
    try:
        # Read image bytes
        image_bytes = await image.read()
        
        # Parse the receipt
        expense = parse_receipt(image_bytes, context)
        
        # Save to file
        saved_path = save_expense(expense)
        
        return {
            "expense": expense.model_dump(),
            "saved_path": saved_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}



