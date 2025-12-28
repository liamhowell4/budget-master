"""
Personal Expense Tracker - Streamlit UI

Features:
- Dashboard: Budget status with progress bars
- Add Expense: Manual entry form (text + optional image)
- History: Expense table with filters and CSV download
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import io

# API Configuration
API_URL = "http://localhost:8000"

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


def submit_expense(text: str = None, image_file=None):
    """Submit expense to API."""
    try:
        files = {}
        data = {}

        if text:
            data["text"] = text

        if image_file:
            files["image"] = (image_file.name, image_file.getvalue(), image_file.type)

        response = requests.post(
            f"{API_URL}/streamlit/process",
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


def render_dashboard():
    """Render the budget dashboard tab."""
    st.header("📊 Budget Dashboard")

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

    # Summary metrics
    st.markdown("---")
    st.subheader("Monthly Summary")

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
        st.progress(min(percentage / 100, 1.0))

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


def render_add_expense():
    """Render the add expense form tab."""
    st.header("➕ Add Expense")

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
                success, result = submit_expense(expense_text, uploaded_image)

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
    st.caption("Track expenses via SMS or web UI with real-time budget monitoring")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add Expense", "📜 History"])

    with tab1:
        render_dashboard()

    with tab2:
        render_add_expense()

    with tab3:
        render_history()


if __name__ == "__main__":
    main()
