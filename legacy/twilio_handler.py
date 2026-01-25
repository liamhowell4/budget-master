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
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .firebase_client import FirebaseClient
from .budget_manager import BudgetManager
from .expense_parser import parse_receipt, detect_recurring
from .output_schemas import Expense, ExpenseType, Date
from .recurring_manager import RecurringManager

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

        OPTIMIZED: Uses batch query to fetch all expenses in one Firestore call
        instead of one query per category (12+ queries -> 1 query).

        Returns:
            Formatted status message
        """
        year, month = self.get_current_date()
        month_name = datetime(year, month, 1).strftime("%b %Y")

        response_lines = [f"📊 Budget Status ({month_name})"]

        # OPTIMIZATION: Get ALL spending in one query
        category_spending = self.budget_manager.get_monthly_spending_by_category(year, month)

        # OPTIMIZATION: Get ALL budget caps in one query
        all_caps = self.firebase.get_all_budget_caps()

        # Categories above 50% threshold
        above_threshold = []
        below_threshold = []

        for expense_type in ExpenseType:
            # Get spending (from batch query result)
            spending = category_spending.get(expense_type.name, 0)

            if spending == 0:
                continue  # Skip categories with no spending

            # Get cap (from batch query result)
            cap = all_caps.get(expense_type.name, 0)
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

        # Add total budget (calculate from category_spending)
        total_spending = sum(category_spending.values())
        total_cap = all_caps.get("TOTAL", 0)
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

    def handle_confirmation_response(self, text: str, pending: Dict) -> Tuple[str, bool]:
        """
        Handle user response to pending expense confirmation.

        Args:
            text: User's SMS response
            pending: Pending expense dict from Firestore

        Returns:
            Tuple of (response_message, should_send_next_pending)
        """
        action, adjusted_amount = RecurringManager.parse_confirmation_response(text)

        year, month = self.get_current_date()
        today = datetime.now(self.timezone).date()
        today_date = Date(day=today.day, month=today.month, year=today.year)

        if action == "YES":
            # Confirm expense - move to expenses collection
            pending_obj = self.firebase._dict_to_pending_expense(pending, pending["pending_id"])
            expense = RecurringManager.pending_to_expense(pending_obj, adjusted_amount)

            # Save expense
            doc_id = self.firebase.save_expense(expense, input_type="recurring")

            # Update recurring template's last_user_action
            self.firebase.update_recurring_expense(
                pending["template_id"],
                {"last_user_action": {
                    "day": today_date.day,
                    "month": today_date.month,
                    "year": today_date.year
                }}
            )

            # Delete pending expense
            self.firebase.delete_pending_expense(pending["pending_id"])

            # Get budget warning
            warning = self.budget_manager.get_budget_warning(
                category=expense.category,
                amount=expense.amount,
                year=year,
                month=month
            )

            # Format confirmation
            amount_to_show = adjusted_amount if adjusted_amount else expense.amount
            response = f"✅ Saved ${amount_to_show:.2f} {expense.expense_name} ({expense.category.name})"

            if warning:
                response += f"\n{warning}"

            return response, True  # Send next pending

        elif action == "SKIP":
            # Skip this occurrence
            # Update recurring template's last_user_action
            self.firebase.update_recurring_expense(
                pending["template_id"],
                {"last_user_action": {
                    "day": today_date.day,
                    "month": today_date.month,
                    "year": today_date.year
                }}
            )

            # Delete pending expense
            self.firebase.delete_pending_expense(pending["pending_id"])

            response = f"⏭️ Skipped {pending['expense_name']} for this month"

            return response, True  # Send next pending

        elif action == "CANCEL":
            # Ask for double confirmation
            response = f"This will delete your {pending['expense_name']} recurring expense. Reply DELETE to confirm."
            return response, False  # Don't send next pending yet

        elif action == "DELETE":
            # Confirmed deletion - delete recurring template
            self.firebase.delete_recurring_expense(pending["template_id"])

            # Delete pending expense
            self.firebase.delete_pending_expense(pending["pending_id"])

            response = f"🗑️ Deleted recurring {pending['expense_name']} expense"

            return response, True  # Send next pending

        else:
            # Unknown response - treat as new message
            return None, False

    def handle_recurring_creation(self, text: str) -> str:
        """
        Handle creation of a new recurring expense via SMS.

        Args:
            text: User's SMS text

        Returns:
            Response message (confirmation request)
        """
        # Detect if recurring
        detection = detect_recurring(text)

        # DEBUG: Log what AI detected
        print(f"🔍 RECURRING DETECTION DEBUG:")
        print(f"   Text: {text}")
        print(f"   is_recurring: {detection.is_recurring}")
        print(f"   confidence: {detection.confidence}")
        print(f"   explanation: {detection.explanation}")
        if detection.recurring_expense:
            print(f"   Parsed expense: {detection.recurring_expense}")
        else:
            print(f"   recurring_expense: None")

        if not detection.is_recurring or not detection.recurring_expense:
            # Not recurring, process as regular expense
            print(f"   ❌ Not processing as recurring")
            return None

        recurring = detection.recurring_expense

        # Format confirmation message
        freq_display = recurring.frequency.value.capitalize()

        if recurring.frequency.value == "monthly":
            if recurring.last_of_month:
                day_display = "last day of month"
            else:
                day_display = f"{recurring.day_of_month}"
        else:
            # Weekly/Biweekly
            weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_display = weekdays[recurring.day_of_week] if recurring.day_of_week is not None else "Unknown"

        response = f"Create recurring expense: {recurring.expense_name}, ${recurring.amount:.2f}, {freq_display}"
        if recurring.frequency.value == "monthly":
            response += f" on {day_display}"
        else:
            response += f" on {day_display}s"

        response += f", Category: {recurring.category.name}? Reply YES to create or NO to cancel"

        # Store in a temporary collection or use a simple state tracker
        # For now, we'll save to a special "pending_recurring_creation" collection
        # Actually, let's use a simpler approach - we'll handle this in handle_webhook by checking if the previous message was a creation request

        # Save to Firestore temporarily (we'll handle YES/NO in handle_webhook)
        temp_data = {
            "expense_name": recurring.expense_name,
            "amount": recurring.amount,
            "category": recurring.category.name,
            "frequency": recurring.frequency.value,
            "day_of_month": recurring.day_of_month,
            "day_of_week": recurring.day_of_week,
            "last_of_month": recurring.last_of_month,
            "awaiting_confirmation": True,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        self.firebase.db.collection("pending_recurring_creation").add(temp_data)

        return response

    def process_expense(self, text: Optional[str], images: List[bytes]) -> Tuple[str, bool]:
        """
        Process an expense from text and/or images.

        Args:
            text: Optional text message
            images: List of image bytes (0-3 images)

        Returns:
            Tuple of (SMS response message, should_check_next_pending)
        """
        print(f"\n{'='*60}")
        print(f"🔍 PROCESS_EXPENSE DEBUG START")
        print(f"   Text: '{text}'")
        print(f"   Images: {len(images)} image(s)")
        print(f"{'='*60}\n")

        year, month = self.get_current_date()

        # Check for commands first
        if text:
            text_lower = text.lower().strip()
            print(f"📝 Checking commands... text_lower='{text_lower}'")
            if text_lower == "status":
                print(f"   ✅ Command detected: status")
                return self.handle_status_command(), False
            elif text_lower == "total":
                print(f"   ✅ Command detected: total")
                return self.handle_total_command(), False
            print(f"   ❌ Not a command")

        # Must have text or images
        if not text and not images:
            print(f"❌ No text or images provided")
            return "❌ Please send an expense (text or receipt image)", False

        try:
            # Check if this is a response to pending recurring creation
            if text and text.lower().strip() in ["yes", "no"]:
                # Check for pending creation
                pending_creation_query = self.firebase.db.collection("pending_recurring_creation").where(
                    filter=FieldFilter("awaiting_confirmation", "==", True)
                ).order_by("created_at", direction=firestore.Query.DESCENDING).limit(1)

                pending_creation_docs = list(pending_creation_query.stream())

                if pending_creation_docs:
                    doc = pending_creation_docs[0]
                    data = doc.to_dict()

                    if text.lower().strip() == "yes":
                        # Create recurring expense
                        from .output_schemas import RecurringExpense, ExpenseType, FrequencyType

                        category = ExpenseType[data["category"]]
                        frequency = FrequencyType[data["frequency"].upper()]

                        recurring = RecurringExpense(
                            expense_name=data["expense_name"],
                            amount=data["amount"],
                            category=category,
                            frequency=frequency,
                            day_of_month=data.get("day_of_month"),
                            day_of_week=data.get("day_of_week"),
                            last_of_month=data.get("last_of_month", False),
                            last_reminded=None,
                            last_user_action=None,
                            active=True
                        )

                        template_id = self.firebase.save_recurring_expense(recurring)

                        # Delete pending creation
                        self.firebase.db.collection("pending_recurring_creation").document(doc.id).delete()

                        # Check if we need to create a pending expense retroactively
                        from datetime import date
                        should_create, trigger_date = RecurringManager.should_create_pending(recurring)

                        if trigger_date:
                            # Trigger date is in the past, create pending immediately
                            today = date.today()
                            if trigger_date <= today:
                                # Update recurring with template_id
                                recurring.template_id = template_id

                                # Create pending expense
                                pending = RecurringManager.create_pending_expense_from_recurring(recurring, trigger_date)
                                pending_id = self.firebase.save_pending_expense(pending)

                                # Update last_reminded
                                today_date = Date(day=today.day, month=today.month, year=today.year)
                                self.firebase.update_recurring_expense(
                                    template_id,
                                    {"last_reminded": {
                                        "day": today_date.day,
                                        "month": today_date.month,
                                        "year": today_date.year
                                    }}
                                )

                                # Send combined confirmation
                                response = f"✅ Created recurring {recurring.expense_name} expense. Since {trigger_date.month}/{trigger_date.day}/{trigger_date.year} already passed, confirm now: {recurring.expense_name} ${recurring.amount:.2f} due {trigger_date.month}/{trigger_date.day}/{trigger_date.year}. Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"

                                # Update pending to mark SMS as sent
                                self.firebase.update_pending_expense(pending_id, {"sms_sent": True})

                                return response, False
                            else:
                                return f"✅ Created recurring {recurring.expense_name} expense", False
                        else:
                            return f"✅ Created recurring {recurring.expense_name} expense", False

                    else:  # "no"
                        # Cancel creation
                        self.firebase.db.collection("pending_recurring_creation").document(doc.id).delete()
                        return "❌ Canceled recurring expense creation", False

            # Check if this is text-only (might be recurring)
            if text and not images:
                print(f"\n🔍 Checking if text is recurring...")
                print(f"   text='{text}', images={len(images)}")
                recurring_response = self.handle_recurring_creation(text)
                print(f"   recurring_response returned: {recurring_response[:100] if recurring_response else 'None'}...")
                if recurring_response:
                    print(f"   ✅ Processing as recurring creation")
                    return recurring_response, False
                else:
                    print(f"   ❌ Not recurring, continuing to regular expense processing")

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
                return "❌ Couldn't find an amount. Please send a complete expense with an amount.\n\nExample: 'Coffee $5' or a clear receipt photo.\n\n(Note: I only process one message at a time, not previous messages)", False

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
                return "❌ Failed to save expense. Please try again.", False

            # Format confirmation message (Option B - Detailed)
            date_str = f"{expense.date.month}/{expense.date.day}/{expense.date.year}"
            response = f"✅ Saved ${expense.amount:.2f} {expense.expense_name} ({expense.category.name}) on {date_str}"

            # Add budget warnings if any
            if warning:
                response += f"\n{warning}"

            return response, True  # Check for next pending

        except Exception as e:
            print(f"Error processing expense: {e}")
            import traceback
            traceback.print_exc()
            return "❌ Sorry, I couldn't parse that expense. Please try again with format: 'Description $amount' or a clear receipt photo", False

    def handle_webhook(self, from_number: str, form_data: dict) -> str:
        """
        Main webhook handler - processes incoming message and returns response.

        Flow:
        1. Check for pending expenses awaiting confirmation
        2. If pending exists, handle as confirmation response
        3. Otherwise, process as regular expense or recurring creation
        4. After processing, check for next pending and send if exists

        Args:
            from_number: Phone number message came from
            form_data: Twilio webhook form data

        Returns:
            Response message to send back
        """
        print(f"\n{'='*80}")
        print(f"📨 WEBHOOK RECEIVED")
        print(f"   From: {from_number}")
        print(f"   Body: {form_data.get('Body', '')}")
        print(f"   NumMedia: {form_data.get('NumMedia', 0)}")
        print(f"{'='*80}\n")

        # Verify it's from the authorized user
        if from_number != self.user_phone:
            print(f"❌ Unauthorized number: {from_number} (expected {self.user_phone})")
            return "❌ Unauthorized number"

        # Parse incoming message
        text, images = self.parse_incoming_message(form_data)
        print(f"📝 Parsed message:")
        print(f"   Text: '{text}'")
        print(f"   Images: {len(images)}")

        # Check for pending expenses first
        pending_expenses = self.firebase.get_all_pending_expenses(awaiting_only=True)

        if pending_expenses and text:
            # User might be responding to pending confirmation
            # Check if text matches confirmation patterns
            action, _ = RecurringManager.parse_confirmation_response(text)

            if action in ["YES", "SKIP", "CANCEL", "DELETE"]:
                # This is likely a confirmation response
                first_pending = pending_expenses[0]

                # Handle confirmation
                response, should_send_next = self.handle_confirmation_response(text, first_pending)

                if response:
                    # Valid confirmation response
                    if should_send_next:
                        # Check for next pending expense
                        remaining_pending = self.firebase.get_all_pending_expenses(awaiting_only=True)

                        if remaining_pending:
                            # Send next pending confirmation
                            next_pending = remaining_pending[0]
                            pending_obj = self.firebase._dict_to_pending_expense(next_pending, next_pending["pending_id"])

                            total_pending = len(remaining_pending)
                            confirmation_msg = RecurringManager.format_confirmation_sms(
                                pending_obj,
                                pending_count=0,
                                total_pending=total_pending
                            )

                            # Mark as SMS sent
                            self.firebase.update_pending_expense(next_pending["pending_id"], {"sms_sent": True})

                            response += f"\n\n{confirmation_msg}"

                    return response

        # Not a confirmation response (or no pending) - process as regular expense
        response, should_check_next = self.process_expense(text, images)

        # After processing, check if there are pending expenses to send
        if should_check_next:
            pending_expenses = self.firebase.get_all_pending_expenses(awaiting_only=True)

            if pending_expenses:
                # Send first pending confirmation
                first_pending = pending_expenses[0]
                pending_obj = self.firebase._dict_to_pending_expense(first_pending, first_pending["pending_id"])

                total_pending = len(pending_expenses)
                confirmation_msg = RecurringManager.format_confirmation_sms(
                    pending_obj,
                    pending_count=0,
                    total_pending=total_pending
                )

                # Mark as SMS sent
                self.firebase.update_pending_expense(first_pending["pending_id"], {"sms_sent": True})

                response += f"\n\n{confirmation_msg}"

        return response
