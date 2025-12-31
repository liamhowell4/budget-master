# Recurring Expenses Implementation Plan

## Overview
Implement auto-create with SMS confirmation system for recurring expenses. System automatically creates pending expenses on schedule, sends SMS for confirmation, and handles YES/SKIP/CANCEL responses.

---

## Architecture Components

### 1. New Firestore Collections

#### `recurring_expenses/` Collection
```javascript
{
  template_id: auto-generated,
  expense_name: "Rent",
  amount: 1000.00,
  category: "RENT", // ExpenseType enum key
  frequency: "monthly" | "weekly" | "biweekly",
  day_of_month: 1, // for monthly (1-31)
  day_of_week: 0, // for weekly/biweekly (0=Monday, 6=Sunday)
  last_of_month: false, // true if user said "last day" explicitly
  last_reminded: { day, month, year }, // when we last created pending expense
  last_user_action: { day, month, year }, // when user last confirmed/skipped/edited
  active: true, // false if user canceled
  created_at: Firebase timestamp
}
```

#### `pending_expenses/` Collection
```javascript
{
  pending_id: auto-generated,
  template_id: "ref_to_recurring_expense",
  expense_name: "Rent",
  amount: 1000.00,
  date: { day, month, year }, // when expense is due
  category: "RENT",
  created_at: Firebase timestamp,
  sms_sent: true, // whether SMS confirmation was sent
  awaiting_confirmation: true // false once user responds
}
```

---

## Implementation Flow

### A. Creating Recurring Expenses

#### SMS Creation Flow
1. User texts: "recurring rent $1000 monthly on the 1st"
2. AI detects keywords: recurring, recur, subscription, monthly, weekly, daily
3. Parse using GPT with enhanced prompt for recurring detection
4. Send confirmation SMS: "Create recurring expense: Rent, $1000, Monthly on 1st, Category: RENT? Reply YES to create or NO to cancel"
5. User replies YES → Create template in `recurring_expenses/` collection
6. Bot replies: "✅ Created recurring Rent expense. Since Dec 1st already passed, confirm now: Rent $1000 due Dec 1. Reply YES, SKIP, or CANCEL."
   - If creation date is BEFORE trigger date, immediately create pending expense
   - If creation date is AFTER trigger date, wait until next occurrence

#### Streamlit Creation Flow
1. User fills form:
   - Expense Name
   - Amount
   - Category (dropdown)
   - Frequency (Monthly/Weekly/Biweekly)
   - Day of Month (1-31) OR Day of Week (Mon-Sun) OR "Last day of month" checkbox
2. Click "Create Recurring Expense"
3. Create template in `recurring_expenses/`
4. If retroactive (trigger date passed), create pending expense immediately
5. Show in pending expenses section with Confirm/Edit/Delete buttons

---

### B. Checking for Due Recurring Expenses

#### Trigger Logic (On API Startup - Pre-Cloud Functions)
```python
For each recurring_expense in recurring_expenses/ where active=true:
    trigger_time = calculate_most_recent_trigger_date(recurring_expense)

    if recurring_expense.last_reminded < trigger_time:
        # Need to create pending expense
        create_pending_expense(recurring_expense)
        recurring_expense.last_reminded = today

    elif recurring_expense.last_reminded >= trigger_time:
        if recurring_expense.last_user_action > recurring_expense.last_reminded:
            # User already handled it, do nothing
            pass
        else:
            # Still pending in Streamlit, keep showing it
            pass
```

**IMPORTANT NOTE FOR CLOUD FUNCTIONS MIGRATION:**
- Current: Check on API startup only
- Future: Cloud Scheduler runs daily, calls `/admin/check-recurring` endpoint
- Change trigger from "on startup" to "daily scheduled job"

---

### C. SMS Confirmation Flow

#### Happy Path - Immediate Confirmation
1. System creates pending expense for "Rent $1000 due Dec 1"
2. Send SMS: "Rent $1000 due Dec 1. Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"
3. User replies: "YES"
4. Move from `pending_expenses/` to `expenses/` collection
5. Update `recurring_expense.last_user_action = today`
6. Reply: "✅ Saved $1000 Rent (RENT) ℹ️ 45% of monthly budget used"
7. If more pending expenses exist, send next confirmation immediately

#### Adjustment Flow
1. User replies: "YES $1050"
2. Parse adjusted amount
3. Save to `expenses/` with adjusted amount ($1050 instead of $1000)
4. Update `recurring_expense.last_user_action = today`
5. Reply with confirmation

#### Skip Flow
1. User replies: "SKIP"
2. Delete pending expense (don't save to expenses)
3. Update `recurring_expense.last_user_action = today`
4. Reply: "⏭️ Skipped Rent for this month"
5. Send next pending confirmation if exists

#### Cancel Flow
1. User replies: "CANCEL"
2. Send double-confirmation: "This will delete your Rent recurring expense. Reply DELETE to confirm."
3. User replies: "DELETE"
4. Delete from `recurring_expenses/` (set active=false or delete document)
5. Delete associated pending expense
6. Reply: "🗑️ Deleted recurring Rent expense"

#### Non-Confirmation Text Flow
1. Pending: "Rent $1000 due Dec 1"
2. User texts: "coffee $5"
3. Process coffee expense normally
4. Reply: "✅ Saved $5 Coffee (COFFEE)"
5. Immediately after: "Rent $1000 due Dec 1. Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"

---

### D. Multiple Pending Expenses on Same Day

#### Sequential Confirmation with Count
1. Rent and Phone Bill both due Dec 1
2. First text at 9am: "You have 2 recurring expenses due today. Rent $1000 due Dec 1. Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"
3. User replies YES
4. Bot: "✅ Saved $1000 Rent (RENT)"
5. Immediately after: "Phone Bill $100 due Dec 1 (1 of 2 remaining). Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"
6. Continue until all confirmed/skipped

---

### E. Streamlit UI Changes

#### Pending Expenses Section (Dashboard Tab)
- Show table with pending expenses:
  - Columns: Expense Name, Amount, Due Date, Category, Actions
  - Actions: Confirm, Edit, Delete buttons
- Edit modal allows full editing: amount, date, category
- Confirm → moves to expenses, updates last_user_action
- Delete → removes pending expense only (doesn't affect template)

#### Recurring Templates Management Section
- Show table with all recurring templates:
  - Columns: Name, Amount, Frequency, Next Due, Status, Actions
  - Status: Active/Paused/Canceled
  - Actions: Edit, Pause, Delete buttons
- Edit modal: Change amount, frequency, day, category
- Pause: Sets active=false temporarily (can reactivate later)
- Delete: Sets active=false permanently (or deletes document)

#### Dashboard Tab Indicator
- If pending_expenses exist with awaiting_confirmation=true:
  - Tab name: "Dashboard ! (2)" where 2 is count
- Otherwise: "Dashboard"

#### Budget View - Projected Budget
- Current Budget: Confirmed expenses only (existing logic)
- Projected Budget: Confirmed + All active recurring templates (assume they'll be paid)
  - Show side-by-side bars: "Current" vs "Projected"
  - Example:
    - Current: $1,200 / $2,000 (60%)
    - Projected: $1,800 / $2,000 (90%) - includes $600 in recurring expenses

---

## Data Schemas (Pydantic Models)

### RecurringExpense
```python
class FrequencyType(Enum):
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"

class RecurringExpense(BaseModel):
    template_id: Optional[str] = None
    expense_name: str
    amount: float
    category: ExpenseType
    frequency: FrequencyType
    day_of_month: Optional[int] = None  # 1-31 for monthly
    day_of_week: Optional[int] = None  # 0-6 for weekly/biweekly
    last_of_month: bool = False
    last_reminded: Optional[Date] = None
    last_user_action: Optional[Date] = None
    active: bool = True
```

### PendingExpense
```python
class PendingExpense(BaseModel):
    pending_id: Optional[str] = None
    template_id: str
    expense_name: str
    amount: float
    date: Date
    category: ExpenseType
    sms_sent: bool = False
    awaiting_confirmation: bool = True
```

### RecurringDetectionResult
```python
class RecurringDetectionResult(BaseModel):
    is_recurring: bool
    confidence: float  # 0-1
    recurring_expense: Optional[RecurringExpense] = None
    explanation: str  # Why AI thinks it's recurring
```

---

## File Changes

### New Files
1. `backend/recurring_manager.py` - Core recurring logic
2. `RECURRING_IMPLEMENTATION_PLAN.md` - This file

### Modified Files
1. `backend/output_schemas.py` - Add RecurringExpense, PendingExpense, FrequencyType schemas
2. `backend/expense_parser.py` - Add `detect_recurring()` function
3. `backend/firebase_client.py` - Add methods for recurring/pending collections
4. `backend/twilio_handler.py` - Add confirmation flow handling
5. `backend/api.py` - Add startup check for recurring expenses
6. `frontend/app.py` - Add pending expenses section, recurring templates UI, dashboard indicator
7. `backend/budget_manager.py` - Add projected budget calculation
8. `CLAUDE.md` - Document recurring expenses feature

---

## Testing Checklist

### SMS Testing
- [ ] Create recurring via SMS with natural language
- [ ] Confirm creation with YES
- [ ] Cancel creation with NO
- [ ] Respond YES to pending expense
- [ ] Respond YES $1050 to adjust amount
- [ ] Respond SKIP to skip occurrence
- [ ] Respond CANCEL to delete template (with DELETE confirmation)
- [ ] Send non-confirmation text while pending exists (should re-prompt)
- [ ] Test multiple pending on same day (sequential flow)

### Streamlit Testing
- [ ] Create monthly recurring (specific day)
- [ ] Create monthly recurring (last day of month)
- [ ] Create weekly recurring
- [ ] Create biweekly recurring
- [ ] Edit pending expense (amount, date, category)
- [ ] Confirm pending expense via button
- [ ] Delete pending expense via button
- [ ] Edit recurring template
- [ ] Pause/reactivate recurring template
- [ ] Delete recurring template
- [ ] Verify dashboard indicator shows count
- [ ] Verify projected budget calculation

### Edge Cases
- [ ] Create recurring on 31st (test Feb, Apr, Jun behavior)
- [ ] Create recurring retroactively (past trigger date)
- [ ] Multiple pending expenses due same day
- [ ] API restart doesn't duplicate pending expenses
- [ ] User ignores pending for weeks (stays in Streamlit)

---

## Deployment Notes

### Pre-Cloud Functions (Current)
- Check recurring on API startup
- Store `last_reminded` field to prevent duplicates
- No automated SMS sending (only when Streamlit/API is active)

### Post-Cloud Functions Migration
- Deploy Cloud Scheduler (daily cron job at midnight)
- Cloud Function calls `/admin/check-recurring` endpoint
- Automated SMS sending at trigger time
- Update CLAUDE.md with deployment instructions

---

## Future Enhancements
- Annual recurring expenses
- Custom intervals (every X days)
- Recurring expense templates (duplicate existing expense as recurring)
- Budget forecasting (project next 3 months based on recurring)
- Smart reminders (text user day before due date)
