"""
Personal Expense Tracker - Streamlit UI

Features:
- Chat: SMS-like interface for quick expense entry
- Dashboard: Budget status with progress bars
- Add Expense: Manual entry form (text + optional image)
- History: Expense table with filters and CSV download
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import io
import json
import os
import uuid

# API Configuration
# Default to Cloud Run, but allow override with BACKEND_URL env var
API_URL = os.getenv("BACKEND_URL", "https://expense-tracker-857587891388.us-central1.run.app")

# Claude-themed color scheme
COLORS = {
    "green": "#10a37f",      # <50%
    "blue": "#3b82f6",       # 50-89%
    "orange": "#f97316",     # 90-99%
    "red": "#ef4444",        # 100%+
    "claude_orange": "#CC785C",  # Claude brand color
    "bg_light": "#f7f7f8",
    "bg_dark": "#1a1a1a"
}


def get_budget_color(percentage: float) -> str:
    """Get color based on budget percentage."""
    if percentage >= 100:
        return COLORS["red"]
    elif percentage >= 90:
        return COLORS["orange"]
    elif percentage >= 50:
        return COLORS["blue"]
    else:
        return COLORS["green"]


def fetch_budget_data(year: int = None, month: int = None):
    """Fetch budget data from API."""
    try:
        params = {}
        if year:
            params["year"] = year
        if month:
            params["month"] = month

        response = requests.get(f"{API_URL}/budget", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Could not connect to API. Make sure the server is running: `uvicorn api:app --reload`")
        return None
    except Exception as e:
        st.error(f"Error fetching budget data: {e}")
        return None


def fetch_expenses(year: int = None, month: int = None, category: str = None):
    """Fetch expense history from API."""
    try:
        params = {}
        if year:
            params["year"] = year
        if month:
            params["month"] = month
        if category:
            params["category"] = category

        response = requests.get(f"{API_URL}/expenses", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Could not connect to API. Make sure the server is running.")
        return None
    except Exception as e:
        st.error(f"Error fetching expenses: {e}")
        return None


def fetch_pending_expenses():
    """Fetch pending expenses awaiting confirmation."""
    try:
        response = requests.get(f"{API_URL}/pending", timeout=10)
        response.raise_for_status()
        return response.json().get("pending_expenses", [])
    except Exception as e:
        st.error(f"Error fetching pending expenses: {e}")
        return []


def fetch_recurring_expenses():
    """Fetch recurring expense templates."""
    try:
        response = requests.get(f"{API_URL}/recurring", timeout=10)
        response.raise_for_status()
        return response.json().get("recurring_expenses", [])
    except Exception as e:
        st.error(f"Error fetching recurring expenses: {e}")
        return []


def confirm_pending_expense(pending_id: str, adjusted_amount: float = None):
    """Confirm a pending expense."""
    try:
        params = {}
        if adjusted_amount:
            params["adjusted_amount"] = adjusted_amount

        response = requests.post(
            f"{API_URL}/pending/{pending_id}/confirm",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return True, "Expense confirmed"
    except Exception as e:
        return False, str(e)


def delete_pending_expense(pending_id: str):
    """Delete/skip a pending expense."""
    try:
        response = requests.delete(f"{API_URL}/pending/{pending_id}", timeout=10)
        response.raise_for_status()
        return True, "Pending expense deleted"
    except Exception as e:
        return False, str(e)


def delete_recurring_template(template_id: str):
    """Delete a recurring expense template."""
    try:
        response = requests.delete(f"{API_URL}/recurring/{template_id}", timeout=10)
        response.raise_for_status()
        return True, "Recurring expense deleted"
    except Exception as e:
        return False, str(e)


def submit_expense(text: str = None, image_file=None, session_id: str = None):
    """Submit expense to API."""
    try:
        files = {}
        data = {}

        if text:
            data["text"] = text

        if session_id:
            data["user_id"] = session_id  # Pass session_id as user_id for conversation tracking

        if image_file:
            files["image"] = (image_file.name, image_file.getvalue(), image_file.type)

        response = requests.post(
            f"{API_URL}/mcp/process_expense",
            files=files if files else None,
            data=data if data else None,
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return False, error_detail
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to API. Make sure the server is running."
    except Exception as e:
        return False, str(e)


def escape_markdown_dollars(text: str) -> str:
    """Escape dollar signs for Streamlit markdown display."""
    return text.replace("$", "\\$")


def process_chat_message(text: str = None, image_file=None, session_id: str = None):
    """
    Process a chat message (text and/or image) and return a formatted SMS-like response.

    Args:
        text: Optional text message
        image_file: Optional uploaded image file
        session_id: Optional session ID for conversation tracking

    Returns:
        tuple: (success: bool, response_message: str, expense_data: dict or None)
    """
    success, result = submit_expense(text, image_file, session_id)

    if not success:
        return False, f"❌ Error: {result}", None

    # Check if this is a command response (no expense data)
    if result.get('amount') is None and result.get('expense_name') is None:
        # This is a command response (status/total)
        response_message = escape_markdown_dollars(result['message'])
        return True, response_message, result

    # Check if this is a recurring expense (message contains "recurring" or "Pending confirmation")
    api_message = result.get('message', '')
    if 'recurring' in api_message.lower() or 'pending confirmation' in api_message.lower():
        # Use the API's message directly for recurring expenses
        response_message = escape_markdown_dollars(api_message)
        return True, response_message, result

    # Format regular expense response to match SMS style
    response_parts = []

    # Success message with emoji (escape dollar signs for markdown)
    response_parts.append(f"✅ Saved \\${result['amount']:.2f} {result['expense_name']} ({result['category']})")

    # Add budget warning if present (escape dollar signs)
    if result.get('budget_warning'):
        response_parts.append(escape_markdown_dollars(result['budget_warning']))

    response_message = "\n".join(response_parts)

    return True, response_message, result


def render_chat():
    """Render the chat interface tab (SMS-like experience)."""
    # Header with clear button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("💬 Chat")
        st.caption("Text or send images just like SMS - your personal expense assistant")
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Initialize session_id for conversation tracking
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Show welcome message if chat is empty
    if len(st.session_state.chat_history) == 0:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": "👋 Hey! Send me your expenses and I'll track them for you.\n\nJust text me like:\n• \"Coffee \\$5\"\n• \"Chipotle lunch \\$15 yesterday\"\n• Or upload a receipt photo!"
            }
        ]

    # Initialize processing state
    if 'processing_message' not in st.session_state:
        st.session_state.processing_message = None

    # Create a container for chat messages with a specific height and border
    with st.container(height=700, border=True):
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # Display image if present
                if "image" in message:
                    st.image(message["image"], width=300)

        # If we're processing a message, show it in the container
        if st.session_state.processing_message:
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    # Process the message
                    msg_data = st.session_state.processing_message
                    success, response, expense_data = process_chat_message(
                        msg_data.get("text"),
                        msg_data.get("image"),
                        st.session_state.session_id
                    )

                    # Add assistant response to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response
                    })

                    # Clear processing flag
                    st.session_state.processing_message = None

                    # Rerun to show the response
                    st.rerun()

    # Chat input with image upload option
    col1, col2 = st.columns([4, 1])

    with col2:
        uploaded_image = st.file_uploader(
            "📎",
            type=["jpg", "jpeg", "png"],
            help="Attach a receipt image",
            label_visibility="collapsed",
            key=f"chat_image_{len(st.session_state.chat_history)}"
        )

    with col1:
        user_input = st.chat_input("Type an expense or attach a receipt...")

    # Handle new user input
    if user_input or uploaded_image:
        # Create user message
        user_message = {
            "role": "user",
            "content": user_input if user_input else "📎 [Receipt Image]"
        }

        if uploaded_image:
            user_message["image"] = uploaded_image

        # Add user message to history
        st.session_state.chat_history.append(user_message)

        # Set processing flag with the message data
        st.session_state.processing_message = {
            "text": user_input,
            "image": uploaded_image
        }

        # Trigger a rerun to show user message and process response
        st.rerun()


def render_dashboard():
    """Render the budget dashboard tab."""
    st.header("📊 Budget Dashboard")

    # Fetch pending expenses first
    pending_expenses = fetch_pending_expenses()

    # Show pending expenses section if any exist
    if pending_expenses:
        st.markdown("### ⏳ Pending Confirmations")
        st.markdown(f"**{len(pending_expenses)} recurring expense(s) awaiting confirmation**")

        for pending in pending_expenses:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])

                with col1:
                    st.markdown(f"**{pending['expense_name']}**")
                    date_obj = pending['date']
                    st.caption(f"Due: {date_obj['month']}/{date_obj['day']}/{date_obj['year']}")

                with col2:
                    st.markdown(f"**\\${pending['amount']:.2f}**")

                with col3:
                    st.markdown(f"`{pending['category']}`")

                with col4:
                    if st.button("✅ Confirm", key=f"confirm_{pending['pending_id']}", use_container_width=True):
                        success, msg = confirm_pending_expense(pending['pending_id'])
                        if success:
                            st.success("✅ Confirmed!")
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

                with col5:
                    if st.button("⏭️ Skip", key=f"skip_{pending['pending_id']}", use_container_width=True):
                        success, msg = delete_pending_expense(pending['pending_id'])
                        if success:
                            st.info("Skipped")
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

                st.markdown("---")

    # Date selector
    col1, col2 = st.columns([1, 3])
    with col1:
        now = datetime.now()
        selected_month = st.selectbox(
            "Month",
            range(1, 13),
            index=now.month - 1,
            format_func=lambda x: datetime(2000, x, 1).strftime("%B")
        )
    with col2:
        selected_year = st.number_input("Year", min_value=2020, max_value=2030, value=now.year)

    # Fetch budget data
    budget_data = fetch_budget_data(selected_year, selected_month)

    if not budget_data:
        return

    # Calculate Disposable Budget (Total - Rent)
    rent_data = next((cat for cat in budget_data["categories"] if cat["category"] == "RENT"), None)
    rent_cap = rent_data["cap"] if rent_data else 0
    rent_spent = rent_data["spending"] if rent_data else 0

    disposable_cap = budget_data['total_cap'] - rent_cap
    disposable_spent = budget_data['total_spending'] - rent_spent
    disposable_remaining = disposable_cap - disposable_spent
    disposable_percentage = (disposable_spent / disposable_cap * 100) if disposable_cap > 0 else 0

    # Disposable Budget Ticker
    st.markdown("---")
    st.subheader("💸 Disposable Budget (Excluding Rent)")
    
    d_col1, d_col2, d_col3 = st.columns(3)
    
    with d_col1:
        st.metric(
            "Disposable Spent", 
            f"${disposable_spent:.2f}", 
            f"{disposable_percentage:.1f}%"
        )
        
    with d_col2:
        st.metric(
            "Disposable Remaining", 
            f"${disposable_remaining:.2f}", 
            f"out of ${disposable_cap:.2f}"
        )
        
    with d_col3:
        if disposable_percentage >= 100:
            d_status = "🚨 Over Budget"
        elif disposable_percentage >= 90:
            d_status = "⚠️ Warning"
        elif disposable_percentage >= 50:
            d_status = "ℹ️ On Track"
        else:
            d_status = "✅ Healthy"
        st.metric("Disposable Status", d_status)

    # Summary metrics
    st.markdown("---")
    st.subheader("Monthly Summary (Total)")

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    total_percentage = budget_data["total_percentage"]
    total_color = get_budget_color(total_percentage)

    with metric_col1:
        st.metric(
            "Total Spent",
            f"${budget_data['total_spending']:.2f}",
            f"{total_percentage:.1f}% of budget"
        )

    with metric_col2:
        st.metric(
            "Budget Remaining",
            f"${budget_data['total_remaining']:.2f}",
            f"out of ${budget_data['total_cap']:.2f}"
        )

    with metric_col3:
        # Status indicator
        if total_percentage >= 100:
            status = "🚨 OVER BUDGET"
        elif total_percentage >= 90:
            status = "⚠️ Warning"
        elif total_percentage >= 50:
            status = "ℹ️ On Track"
        else:
            status = "✅ Healthy"

        st.metric("Status", status)

    # Total progress bar
    st.markdown("---")
    st.markdown(f"**Overall Budget Progress**")
    st.progress(min(total_percentage / 100, 1.0))
    st.markdown(
        f"<div style='text-align: center; color: {total_color}; font-weight: bold;'>"
        f"{total_percentage:.1f}% used</div>",
        unsafe_allow_html=True
    )

    # Category breakdown
    st.markdown("---")
    st.subheader("Category Breakdown")

    # Filter to show only categories with caps > 0
    categories = [cat for cat in budget_data["categories"] if cat["cap"] > 0]

    for category in categories:
        name = category["category"]
        emoji = category["emoji"]
        spending = category["spending"]
        cap = category["cap"]
        percentage = category["percentage"]
        remaining = category["remaining"]

        color = get_budget_color(percentage)

        # Category header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{emoji} {name}**")
        with col2:
            st.markdown(
                f"<div style='text-align: right; color: {color}; font-weight: bold;'>"
                f"${spending:.0f} / ${cap:.0f}</div>",
                unsafe_allow_html=True
            )

        # Progress bar
        st.progress(max(0.0, min(percentage / 100, 1.0)))

        # Details
        col1, col2 = st.columns([3, 1])
        with col1:
            if remaining >= 0:
                st.caption(f"${remaining:.2f} remaining")
            else:
                st.caption(f"${abs(remaining):.2f} over budget", help="You've exceeded this budget!")
        with col2:
            st.caption(
                f"<div style='text-align: right; color: {color};'>{percentage:.1f}%</div>",
                unsafe_allow_html=True
            )

        st.markdown("")  # Spacing

    # Projected budget (includes recurring expenses)
    st.markdown("---")
    st.subheader("📈 Projected Budget")
    st.markdown("Includes all active recurring expenses assuming they'll be paid this month")

    # Fetch recurring expenses
    recurring_expenses = fetch_recurring_expenses()
    active_recurring = [r for r in recurring_expenses if r.get('active', True)]

    if active_recurring:
        # Calculate projected spending by category
        projected_spending_by_cat = {}
        for cat_data in categories:
            projected_spending_by_cat[cat_data['category']] = cat_data['spending']

        # Add recurring expenses to projected totals
        total_recurring = 0
        for rec in active_recurring:
            cat = rec['category']
            amount = rec['amount']
            if cat in projected_spending_by_cat:
                projected_spending_by_cat[cat] += amount
            else:
                projected_spending_by_cat[cat] = amount
            total_recurring += amount

        # Show projected total
        projected_total = budget_data['total_spending'] + total_recurring
        projected_percentage = (projected_total / budget_data['total_cap']) * 100 if budget_data['total_cap'] > 0 else 0
        projected_color = get_budget_color(projected_percentage)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Current Spending**")
            st.metric(
                "Confirmed",
                f"${budget_data['total_spending']:.2f}",
                f"{total_percentage:.1f}%"
            )

        with col2:
            st.markdown("**Projected Spending**")
            st.metric(
                "With Recurring",
                f"${projected_total:.2f}",
                f"{projected_percentage:.1f}%",
                delta_color="inverse"
            )

        # Show projection for each category with active recurring
        st.markdown("**Categories with Recurring Expenses:**")
        for cat_data in categories:
            cat_name = cat_data["category"]
            current = cat_data["spending"]
            projected = projected_spending_by_cat.get(cat_name, current)

            if projected > current:  # Only show if there's a projected increase
                emoji = cat_data["emoji"]
                cap = cat_data["cap"]
                if cap > 0:
                    projected_pct = (projected / cap) * 100
                    color = get_budget_color(projected_pct)

                    col1, col2, col3 = st.columns([2, 2, 2])
                    with col1:
                        st.markdown(f"{emoji} **{cat_name}**")
                    with col2:
                        st.markdown(f"Current: \\${current:.0f} → Projected: \\${projected:.0f}")
                    with col3:
                        st.markdown(
                            f"<div style='text-align: right; color: {color};'>{projected_pct:.1f}%</div>",
                            unsafe_allow_html=True
                        )

    else:
        st.info("No active recurring expenses")

    st.markdown("")  # Spacing


def render_recurring():
    """Render the recurring expenses management tab."""
    st.header("🔄 Recurring Expenses")

    st.markdown("""
    Manage your recurring expenses like rent, subscriptions, and bills.
    These will automatically create pending confirmations each period.
    """)

    # Fetch recurring expenses
    recurring_expenses = fetch_recurring_expenses()

    if not recurring_expenses:
        st.info("No recurring expenses yet. Create one in the Chat tab!")
        return

    # Filter buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{len(recurring_expenses)} recurring expense(s)**")
    with col2:
        show_inactive = st.checkbox("Show Inactive", value=False)

    # Filter recurring expenses
    if not show_inactive:
        recurring_expenses = [r for r in recurring_expenses if r.get('active', True)]

    # Display recurring expenses
    for rec in recurring_expenses:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])

            with col1:
                status_emoji = "✅" if rec.get('active', True) else "⏸️"
                st.markdown(f"{status_emoji} **{rec['expense_name']}**")

                # Show frequency details
                freq = rec['frequency']
                if freq == "monthly":
                    if rec.get('last_of_month'):
                        st.caption("Monthly on last day")
                    else:
                        st.caption(f"Monthly on day {rec.get('day_of_month', '?')}")
                elif freq == "weekly":
                    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    day_idx = rec.get('day_of_week', 0)
                    st.caption(f"Weekly on {weekdays[day_idx]}s")
                elif freq == "biweekly":
                    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    day_idx = rec.get('day_of_week', 0)
                    st.caption(f"Biweekly on {weekdays[day_idx]}s")

            with col2:
                st.markdown(f"**\\${rec['amount']:.2f}**")

            with col3:
                st.markdown(f"`{rec['category']}`")

            with col4:
                # Show next due date
                if rec.get('last_reminded'):
                    lr = rec['last_reminded']
                    st.caption(f"Last: {lr['month']}/{lr['day']}")
                else:
                    st.caption("Not triggered yet")

            with col5:
                if st.button("🗑️", key=f"delete_rec_{rec['template_id']}", help="Delete recurring", use_container_width=True):
                    success, msg = delete_recurring_template(rec['template_id'])
                    if success:
                        st.success("Deleted!")
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

            st.markdown("---")


def render_add_expense():
    """Render the add expense form tab."""
    st.header("➕ Add Expense")

    # Initialize session_id for conversation tracking
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    st.markdown("""
    Enter an expense description or upload a receipt image. The AI will automatically:
    - Extract the amount
    - Categorize the expense
    - Parse dates (supports "yesterday", "last Tuesday", etc.)
    """)

    # Text input
    expense_text = st.text_input(
        "Expense Description",
        placeholder='e.g., "Coffee $5", "Chipotle lunch $15 yesterday"',
        help="Describe your expense. Include amount and optionally a date."
    )

    # Image upload
    uploaded_image = st.file_uploader(
        "Receipt Image (Optional)",
        type=["jpg", "jpeg", "png"],
        help="Upload a receipt photo for automatic extraction"
    )

    # Preview image
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded Receipt", use_container_width=True)

    # Submit button
    if st.button("Add Expense", type="primary", use_container_width=True):
        if not expense_text and not uploaded_image:
            st.error("Please provide either a text description or upload a receipt image.")
        else:
            with st.spinner("Processing expense..."):
                success, result = submit_expense(expense_text, uploaded_image, st.session_state.session_id)

                if success:
                    # Display success message
                    st.success(f"✅ {result['message']}")

                    # Show expense details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Amount", f"${result['amount']:.2f}")
                    with col2:
                        st.metric("Category", result['category'])
                    with col3:
                        st.metric("Name", result['expense_name'])

                    # Show budget warning if present
                    if result.get('budget_warning'):
                        warning_lines = result['budget_warning'].split('\n')
                        for line in warning_lines:
                            if '🚨' in line:
                                st.error(line)
                            elif '⚠️' in line:
                                st.warning(line)
                            else:
                                st.info(line)

                    # Trigger dashboard refresh by updating session state
                    st.session_state['refresh_dashboard'] = True

                    # Clear form
                    st.rerun()
                else:
                    st.error(f"❌ {result}")


def render_history():
    """Render the expense history tab."""
    st.header("📜 Expense History")

    # Filters in expander
    with st.expander("🔍 Filters", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)

        with filter_col1:
            now = datetime.now()
            filter_month = st.selectbox(
                "Month",
                range(1, 13),
                index=now.month - 1,
                format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
                key="history_month"
            )

        with filter_col2:
            filter_year = st.number_input(
                "Year",
                min_value=2020,
                max_value=2030,
                value=now.year,
                key="history_year"
            )

        with filter_col3:
            categories = ["All"] + [
                "FOOD_OUT", "RENT", "UTILITIES", "MEDICAL", "GAS",
                "GROCERIES", "RIDE_SHARE", "COFFEE", "HOTEL", "TECH", "TRAVEL", "OTHER"
            ]
            filter_category = st.selectbox("Category", categories, key="history_category")

    # Fetch expenses
    category_param = None if filter_category == "All" else filter_category
    expense_data = fetch_expenses(filter_year, filter_month, category_param)

    if not expense_data:
        return

    expenses = expense_data.get("expenses", [])

    if not expenses:
        st.info("No expenses found for the selected filters.")
        return

    # Convert to DataFrame
    df_data = []
    for exp in expenses:
        date_obj = exp.get("date", {})
        df_data.append({
            "Date": f"{date_obj.get('month', '')}/{date_obj.get('day', '')}/{date_obj.get('year', '')}",
            "Name": exp.get("expense_name", ""),
            "Amount": exp.get("amount", 0),
            "Category": exp.get("category", ""),
            "Input": exp.get("input_type", "")
        })

    df = pd.DataFrame(df_data)

    # Total
    total_amount = df["Amount"].sum()
    st.markdown(f"**Total Expenses:** ${total_amount:.2f} ({len(df)} items)")

    # Data table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn(
                "Amount",
                format="$%.2f"
            )
        }
    )

    # Download CSV button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=f"expenses_{filter_year}_{filter_month:02d}.csv",
        mime="text/csv",
        use_container_width=True
    )


def main():
    """Main Streamlit application."""

    # Page config with Claude theming
    st.set_page_config(
        page_title="Personal Expense Tracker",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS for Claude theming
    st.markdown(f"""
        <style>
        /* Claude-themed colors */
        .stProgress > div > div > div > div {{
            background-color: {COLORS['claude_orange']};
        }}

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {{
            .stApp {{
                background-color: {COLORS['bg_dark']};
            }}
        }}

        /* Header styling */
        h1, h2, h3 {{
            color: {COLORS['claude_orange']};
        }}
        </style>
    """, unsafe_allow_html=True)

    # Title
    st.title("💰 Personal Expense Tracker")
    st.caption("Track expenses via chat, SMS, or web UI with real-time budget monitoring")

    # Check for pending expenses to show badge
    pending_count = len(fetch_pending_expenses())
    dashboard_label = f"📊 Dashboard ! ({pending_count})" if pending_count > 0 else "📊 Dashboard"

    # Tabs - Chat is first (default)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat",
        dashboard_label,
        "🔄 Recurring",
        "➕ Add Expense",
        "📜 History"
    ])

    with tab1:
        render_chat()

    with tab2:
        render_dashboard()

    with tab3:
        render_recurring()

    with tab4:
        render_add_expense()

    with tab5:
        render_history()


if __name__ == "__main__":
    main()
