"""
Azure Function entry point for the Expense Bot.
Receives messages from Azure Bot Service and processes expense receipts.
"""

import azure.functions as func
import logging
import json
import os

from bot_handler import BotHandler

# Initialize the Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Get bot credentials with backwards compatibility for old variable names
BOT_ID = os.getenv("BOT_ID") or os.getenv("APP_ID")
BOT_SECRET = os.getenv("BOT_SECRET") or os.getenv("APP_SECRET")

if not BOT_ID or not BOT_SECRET:
    logging.warning(
        "Bot credentials not found. Please set BOT_ID and BOT_SECRET "
        "(or legacy APP_ID and APP_SECRET) environment variables."
    )
else:
    logging.info(f"Bot initialized with App ID: {BOT_ID}")

# Initialize bot handler
bot_handler = BotHandler(
    app_id=BOT_ID,
    app_secret=BOT_SECRET
)


@app.route(route="messages", methods=["POST"])
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main endpoint for Bot Framework messages.
    Azure Bot Service sends all user messages here.
    """
    logging.info("Received message from Bot Service")
    
    # Validate content type
    if "application/json" not in req.headers.get("Content-Type", ""):
        return func.HttpResponse(
            "Invalid content type",
            status_code=415
        )
    
    try:
        # Parse the incoming activity
        body = req.get_json()
        logging.info(f"Activity type: {body.get('type')}")
        
        # Get auth header for validation
        auth_header = req.headers.get("Authorization", "")
        
        # Process the activity
        response = await bot_handler.process_activity(body, auth_header)
        
        if response:
            return func.HttpResponse(
                json.dumps(response),
                status_code=200,
                mimetype="application/json"
            )
        
        return func.HttpResponse(status_code=200)
        
    except ValueError as e:
        logging.error(f"Invalid JSON: {e}")
        return func.HttpResponse(
            "Invalid JSON payload",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        return func.HttpResponse(
            f"Internal error: {str(e)}",
            status_code=500
        )


@app.route(route="health", methods=["GET"])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy", 
            "service": "expense-bot",
            "bot_configured": bool(BOT_ID and BOT_SECRET)
        }),
        status_code=200,
        mimetype="application/json"
    )

