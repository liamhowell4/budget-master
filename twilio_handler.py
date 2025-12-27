"""
Twilio Handler - Handles SMS/MMS webhook processing and responses.
"""

import os
import requests
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from dotenv import load_dotenv
import pytz

from twilio.rest import Client
from twilio.request_validator import RequestValidator

from firebase_client import FirebaseClient
from budget_manager import BudgetManager
from expense_parser import parse_receipt
from output_schemas import Expense, ExpenseType

load_dotenv(override=True)


class TwilioHandler:
    """Handles Twilio SMS/MMS webhook processing and responses."""

    def __init__(self):
        """Initialize Twilio client and Firebase integration."""
        # Twilio credentials
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")

        self.client = Client(account_sid, auth_token)
        self.auth_token = auth_token
        self.validator = RequestValidator(auth_token)

        # User phone number for verification
        self.user_phone = os.getenv("USER_PHONE_NUMBER")
        if not self.user_phone:
            raise ValueError("USER_PHONE_NUMBER must be set in .env")

        # Timezone
        timezone_str = os.getenv("USER_TIMEZONE", "America/Chicago")
        self.timezone = pytz.timezone(timezone_str)

        # Firebase and Budget Manager
        self.firebase = FirebaseClient()
        self.budget_manager = BudgetManager(self.firebase)

    def validate_request(self, url: str, post_data: dict, signature: str) -> bool:
        """
        Validate that the request came from Twilio.

        Args:
            url: The full URL of your webhook
            post_data: The POST parameters as a dictionary
            signature: The X-Twilio-Signature header value

        Returns:
            True if valid, False otherwise
        """
        return self.validator.validate(url, post_data, signature)

    def download_mms_media(self, media_url: str) -> Optional[bytes]:
        """
        Download media from Twilio MMS.

        Args:
            media_url: The MediaUrl from Twilio webhook

        Returns:
            Image bytes or None if download fails
        """
        try:
            # Twilio media URLs require Basic Auth
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")

            response = requests.get(
                media_url,
                auth=(account_sid, auth_token),
                timeout=10
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Error downloading MMS media: {e}")
            return None

    def parse_incoming_message(self, form_data: dict) -> Tuple[Optional[str], List[bytes]]:
        """
        Parse incoming Twilio webhook data to extract text and images.

        Args:
            form_data: The form data from Twilio webhook (request.form or request.values)

        Returns:
            Tuple of (text_message, list_of_image_bytes)
        """
        # Extract text body
        text = form_data.get("Body", "").strip()

        # Extract media (up to 3 images)
        images = []
        num_media = int(form_data.get("NumMedia", 0))

        for i in range(min(num_media, 3)):  # Max 3 images
            media_url = form_data.get(f"MediaUrl{i}")
            if media_url:
                image_bytes = self.download_mms_media(media_url)
                if image_bytes:
                    images.append(image_bytes)

        return text if text else None, images

    def send_sms(self, to: str, message: str) -> bool:
        """
        Send an SMS message.

        Args:
            to: Recipient phone number
            message: Message text

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from_number = os.getenv("TWILIO_PHONE_NUMBER")
            if not from_number:
                raise ValueError("TWILIO_PHONE_NUMBER not set in .env")

            self.client.messages.create(
                body=message,
                from_=from_number,
                to=to
            )
            return True
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False

    def get_current_date(self) -> Tuple[int, int]:
        """
        Get current year and month in user's timezone.

        Returns:
            Tuple of (year, month)
        """
        now = datetime.now(self.timezone)
        return now.year, now.month

    def handle_status_command(self) -> str:
        """
        Handle 'status' command - show budget status.

        Returns:
            Formatted status message
        """
        year, month = self.get_current_date()
        month_name = datetime(year, month, 1).strftime("%b %Y")

        response_lines = [f"📊 Budget Status ({month_name})"]

        # Categories above 50% threshold
        above_threshold = []
        below_threshold = []

        for expense_type in ExpenseType:
            # Get spending and cap
            spending = self.budget_manager.calculate_monthly_spending(expense_type, year, month)

            if spending == 0:
                continue  # Skip categories with no spending

            cap = self.firebase.get_budget_cap(expense_type.name)
            if not cap or cap == 0:
                continue

            percentage = (spending / cap) * 100
            remaining = cap - spending

            if percentage >= 50:
                # Above threshold - show details with emoji
                if percentage >= 100:
                    emoji = "🚨"
                elif percentage >= 95:
                    emoji = "⚠️"
                elif percentage >= 90:
                    emoji = "⚠️"
                else:
                    emoji = "ℹ️"

                above_threshold.append(
                    f"{expense_type.name}: ${spending:.0f}/${cap:.0f} ({percentage:.0f}%) {emoji}"
                )
            else:
                # Below threshold - just add name to list
                below_threshold.append(expense_type.name)

        # Add above threshold items
        response_lines.extend(above_threshold)

        # Add below threshold list
        if below_threshold:
            response_lines.append(f"<50%: {', '.join(below_threshold)}")

        # Add total budget
        total_spending = self.budget_manager.calculate_total_monthly_spending(year, month)
        total_cap = self.firebase.get_budget_cap("TOTAL")
        if total_cap and total_cap > 0:
            total_percentage = (total_spending / total_cap) * 100
            total_remaining = total_cap - total_spending

            if total_percentage >= 100:
                emoji = "🚨"
            elif total_percentage >= 90:
                emoji = "⚠️"
            elif total_percentage >= 50:
                emoji = "ℹ️"
            else:
                emoji = "✅"

            response_lines.append(
                f"TOTAL: ${total_spending:.0f}/${total_cap:.0f} ({total_percentage:.0f}%) {emoji}"
            )

        return "\n".join(response_lines)

    def handle_total_command(self) -> str:
        """
        Handle 'total' command - show monthly spending total.

        Returns:
            Formatted total message
        """
        year, month = self.get_current_date()
        month_name = datetime(year, month, 1).strftime("%B")

        total_spending = self.budget_manager.calculate_total_monthly_spending(year, month)
        total_cap = self.firebase.get_budget_cap("TOTAL")

        if not total_cap or total_cap == 0:
            return f"💰 {month_name} Total: ${total_spending:.2f}"

        percentage = (total_spending / total_cap) * 100
        remaining = total_cap - total_spending

        response = f"💰 {month_name} Total: ${total_spending:.2f}\n"
        response += f"📊 {percentage:.0f}% of ${total_cap:.0f} budget\n"

        if remaining >= 0:
            response += f"💵 ${remaining:.2f} remaining"
        else:
            response += f"🚨 ${abs(remaining):.2f} over budget"

        return response

    def process_expense(self, text: Optional[str], images: List[bytes]) -> str:
        """
        Process an expense from text and/or images.

        Args:
            text: Optional text message
            images: List of image bytes (0-3 images)

        Returns:
            SMS response message
        """
        year, month = self.get_current_date()

        # Check for commands first
        if text:
            text_lower = text.lower().strip()
            if text_lower == "status":
                return self.handle_status_command()
            elif text_lower == "total":
                return self.handle_total_command()

        # Must have text or images
        if not text and not images:
            return "❌ Please send an expense (text or receipt image)"

        try:
            # Parse expense (handles text, images, or both)
            # For multiple images, use the first one for now
            image_bytes = images[0] if images else None

            expense = parse_receipt(
                image_bytes=image_bytes,
                text=text,
                context=None
            )

            # Validate amount
            if expense.amount == 0:
                return "❌ Couldn't find an amount. Please send a complete expense with an amount.\n\nExample: 'Coffee $5' or a clear receipt photo.\n\n(Note: I only process one message at a time, not previous messages)"

            # Get budget warning BEFORE saving
            warning = self.budget_manager.get_budget_warning(
                category=expense.category,
                amount=expense.amount,
                year=year,
                month=month
            )

            # Save to Firestore (with retry)
            saved = False
            for attempt in range(2):
                try:
                    doc_id = self.firebase.save_expense(expense, input_type="sms")
                    saved = True
                    break
                except Exception as e:
                    if attempt == 0:
                        print(f"Retry saving expense: {e}")
                        continue
                    else:
                        raise

            if not saved:
                return "❌ Failed to save expense. Please try again."

            # Format confirmation message (Option B - Detailed)
            date_str = f"{expense.date.month}/{expense.date.day}/{expense.date.year}"
            response = f"✅ Saved ${expense.amount:.2f} {expense.expense_name} ({expense.category.name}) on {date_str}"

            # Add budget warnings if any
            if warning:
                response += f"\n{warning}"

            return response

        except Exception as e:
            print(f"Error processing expense: {e}")
            return "❌ Sorry, I couldn't parse that expense. Please try again with format: 'Description $amount' or a clear receipt photo"

    def handle_webhook(self, from_number: str, form_data: dict) -> str:
        """
        Main webhook handler - processes incoming message and returns response.

        Args:
            from_number: Phone number message came from
            form_data: Twilio webhook form data

        Returns:
            Response message to send back
        """
        # Verify it's from the authorized user
        if from_number != self.user_phone:
            return "❌ Unauthorized number"

        # Parse incoming message
        text, images = self.parse_incoming_message(form_data)

        # Process the expense
        response = self.process_expense(text, images)

        return response
