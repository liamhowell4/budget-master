"""
Bot Handler - Processes incoming Bot Framework activities.
Handles image downloads from Teams, expense parsing, and user feedback.
"""

import logging
import httpx
import json
import os
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime, timedelta

from expense_parser import parse_receipt
from adaptive_cards import (
    create_expense_card, 
    create_error_card, 
    create_welcome_card,
    create_feedback_response_card
)

load_dotenv()

class BotHandler:
    """Handles Bot Framework message processing."""
    
    def __init__(self, app_id: str, app_secret: str):
        """
        Initialize the bot handler.
        
        Args:
            app_id: Azure AD App Registration Client ID (BOT_ID)
            app_secret: Azure AD App Registration Client Secret (BOT_SECRET)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    async def get_bot_token(self) -> str:
        """
        Get an access token for Bot Framework API calls.
        Used for downloading attachments and sending responses.
        """
        # Check if we have a valid cached token
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token

        # Try botframework.com first (for multi-tenant), fallback to specific tenant
        tenant_id = os.getenv("TENANT_ID")
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        logging.info(f"Requesting token for BOT_ID: {self.app_id} from tenant: {tenant_id}")
        
        # Request new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "scope": "https://api.botframework.com/.default"
                }
            )
            
            if response.status_code != 200:
                logging.error(f"Token request FAILED ({response.status_code}): {response.text}")
                raise Exception(f"Failed to authenticate with Bot Framework: {response.status_code}")
            
            logging.info(f"Token request SUCCEEDED")
            
            token_data = response.json()
            self._token = token_data["access_token"]
            # Set expiry with 5 minute buffer
            expires_in = token_data.get("expires_in", 3600) - 300
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return self._token
    
    async def download_attachment(self, content_url: str) -> bytes:
        """
        Download an attachment from Teams.
        Teams attachments require Bot authentication to download.
        """
        token = await self.get_bot_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                content_url,
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True
            )
            
            if response.status_code != 200:
                logging.error(f"Failed to download attachment: {response.status_code}")
                raise Exception(f"Failed to download attachment: {response.status_code}")
            
            return response.content
    
    async def send_activity(self, service_url: str, conversation_id: str, activity: dict):
        """Send an activity (message) back to the user."""
        token = await self.get_bot_token()
        
        url = f"{service_url.rstrip('/')}/v3/conversations/{conversation_id}/activities"
        
        # Ensure 'from' field is present (required by Web Chat)
        if "from" not in activity:
            activity["from"] = {"id": self.app_id, "name": "Expense Bot"}
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=activity
            )
            
            if response.status_code not in [200, 201]:
                logging.error(f"Failed to send activity to {url}. Status: {response.status_code}. Response: {response.text}")
    
    async def process_activity(self, activity: dict, auth_header: str) -> Optional[dict]:
        """
        Process an incoming Bot Framework activity.
        
        Args:
            activity: The incoming activity JSON
            auth_header: Authorization header for validation
            
        Returns:
            Response to send back (or None)
        """
        activity_type = activity.get("type")
        
        if activity_type == "conversationUpdate":
            # User joined the conversation - send welcome
            return await self._handle_conversation_update(activity)
        
        elif activity_type == "message":
            # Check if this is a card action (feedback submission)
            value = activity.get("value")
            if value and isinstance(value, dict) and value.get("action") == "feedback":
                return await self._handle_feedback(activity)
            
            # Regular message - process as receipt
            return await self._handle_message(activity)
        
        elif activity_type == "invoke":
            # Handle invoke activities (card actions in some cases)
            return await self._handle_invoke(activity)
        
        else:
            logging.info(f"Ignoring activity type: {activity_type}")
            return None
    
    async def _handle_conversation_update(self, activity: dict) -> Optional[dict]:
        """Handle conversation update (user joined)."""
        members_added = activity.get("membersAdded", [])
        bot_id = activity.get("recipient", {}).get("id")
        
        # Check if the bot was added (not the user)
        for member in members_added:
            if member.get("id") != bot_id:
                # User was added, send welcome
                service_url = activity.get("serviceUrl")
                conversation_id = activity.get("conversation", {}).get("id")
                
                welcome_activity = {
                    "type": "message",
                    "attachments": [{
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": create_welcome_card()
                    }]
                }
                
                await self.send_activity(service_url, conversation_id, welcome_activity)
        
        return None
    
    async def _handle_feedback(self, activity: dict) -> Optional[dict]:
        """
        Handle feedback submission from adaptive card buttons.
        """
        service_url = activity.get("serviceUrl")
        conversation_id = activity.get("conversation", {}).get("id")
        value = activity.get("value", {})
        
        feedback_type = value.get("feedback", "unknown")
        card_id = value.get("card_id", "unknown")
        expense_name = value.get("expense_name", "unknown expense")
        user_id = activity.get("from", {}).get("id", "unknown")
        user_name = activity.get("from", {}).get("name", "unknown")
        
        # Log the feedback for analytics
        logging.info(
            f"Feedback received: {feedback_type} | "
            f"Card: {card_id} | "
            f"Expense: {expense_name} | "
            f"User: {user_name} ({user_id})"
        )
        
        # Send acknowledgment card
        feedback_card = create_feedback_response_card(feedback_type, expense_name)
        response_activity = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": feedback_card
            }]
        }
        
        await self.send_activity(service_url, conversation_id, response_activity)
        
        return None
    
    async def _handle_invoke(self, activity: dict) -> Optional[dict]:
        """
        Handle invoke activities (e.g., adaptive card actions).
        Returns a response for invoke activities.
        """
        invoke_name = activity.get("name", "")
        value = activity.get("value", {})
        
        # Handle adaptive card action invoke
        if invoke_name == "adaptiveCard/action":
            action_data = value.get("action", {}).get("data", {})
            
            if action_data.get("action") == "feedback":
                # Process feedback
                service_url = activity.get("serviceUrl")
                conversation_id = activity.get("conversation", {}).get("id")
                
                feedback_type = action_data.get("feedback", "unknown")
                expense_name = action_data.get("expense_name", "unknown")
                card_id = action_data.get("card_id", "unknown")
                
                logging.info(f"Invoke feedback: {feedback_type} for {expense_name}")
                
                # Send acknowledgment
                feedback_card = create_feedback_response_card(feedback_type, expense_name)
                response_activity = {
                    "type": "message",
                    "attachments": [{
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": feedback_card
                    }]
                }
                
                await self.send_activity(service_url, conversation_id, response_activity)
                
                # Return invoke response
                return {
                    "status": 200,
                    "body": {"statusCode": 200}
                }
        
        logging.info(f"Unhandled invoke: {invoke_name}")
        return {"status": 200}
    
    async def _handle_message(self, activity: dict) -> Optional[dict]:
        """
        Handle an incoming message from the user.
        Expects an image attachment with optional text context.
        """
        service_url = activity.get("serviceUrl")
        conversation_id = activity.get("conversation", {}).get("id")
        text = activity.get("text", "").strip()
        attachments = activity.get("attachments", [])
        
        # Find image attachments
        image_attachment = None
        for att in attachments:
            content_type = att.get("contentType", "")
            if content_type.startswith("image/"):
                image_attachment = att
                break
        
        # If no image, send instructions
        if not image_attachment:
            instruction_activity = {
                "type": "message",
                "text": "📸 Please send me a receipt image with an optional caption describing the expense.\n\nExample caption: *Lunch with John Smith (Acme Corp), project Alpha*"
            }
            await self.send_activity(service_url, conversation_id, instruction_activity)
            return None
        
        # Send "processing" message
        processing_activity = {
            "type": "message",
            "text": "⏳ Processing your receipt..."
        }
        await self.send_activity(service_url, conversation_id, processing_activity)
        
        try:
            # Download the image
            content_url = image_attachment.get("contentUrl")
            logging.info(f"Downloading image from: {content_url}")
            image_bytes = await self.download_attachment(content_url)
            
            # Parse the receipt
            logging.info(f"Parsing receipt with context: {text}")
            expense = parse_receipt(image_bytes, text)
            
            # Log the parsed data for debugging
            try:
                logging.info(f"AI Parsed Result: {json.dumps(expense.model_dump(), indent=2, default=str)}")
            except Exception as log_err:
                logging.info(f"AI Parsed Result (raw): {expense}")
            
            # Create and send the Adaptive Card response with feedback buttons
            card = create_expense_card(expense, include_feedback=True)
            response_activity = {
                "type": "message",
                "attachments": [{
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card
                }]
            }
            
            await self.send_activity(service_url, conversation_id, response_activity)
            
        except Exception as e:
            logging.error(f"Error processing receipt: {e}")
            error_card = create_error_card(str(e))
            error_activity = {
                "type": "message",
                "attachments": [{
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": error_card
                }]
            }
            await self.send_activity(service_url, conversation_id, error_activity)
        
        return None

