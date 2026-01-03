# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A personal expense tracking and budgeting app that accepts expenses via multiple input methods:
- **SMS/MMS via Twilio** - Send expense info as text or receipt images from mobile
- **Streamlit Web UI** - Record voice memos or upload images from desktop/web

All inputs are processed using OpenAI APIs (GPT-4 Vision for images, Whisper for voice transcription, GPT for text parsing) and stored in Firebase Firestore. The app focuses on budget management with monthly caps and real-time budget warnings.

**🚧 MIGRATION IN PROGRESS**: The app is currently migrating from OpenAI to Claude+MCP architecture to enable conversational expense management (edit, delete, query expenses via SMS). During migration, both backends will run in parallel. See "MCP Migration" section below for details.

## Environment Setup

Required environment variables in `.env` (DO NOT EDIT .env directly - ask user to update):
- `OPENAI_API_KEY` - OpenAI API key for GPT-4 Vision, GPT text processing, and Whisper
- `FIREBASE_KEY` - Firebase service account key JSON (or path to key file)
- `TWILIO_ACCOUNT_SID` - Twilio Account SID
- `TWILIO_ACCOUNT_TOKEN` - Twilio Account Token
- `TWILIO_SECRET_SID` - Twilio Secret SID
- `TWILIO_SECRET_KEY` - Twilio Secret Key

**IMPORTANT**: Never attempt to edit `.env` file. Always ask the user to add/update environment variables.

Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

The codebase is organized into the following directories:

```
finance_bot/
├── backend/              # FastAPI backend and core logic
│   ├── api.py           # FastAPI app with endpoints
│   ├── expense_parser.py # Expense parsing logic + recurring detection
│   ├── firebase_client.py # Firestore/Storage operations
│   ├── twilio_handler.py # Twilio webhook + confirmation flow
│   ├── budget_manager.py # Budget calculations & warnings
│   ├── recurring_manager.py # Recurring expense logic
│   ├── endpoints.py     # OpenAI client configuration
│   └── output_schemas.py # Pydantic data models
│
├── frontend/            # Streamlit UI
│   └── app.py          # Streamlit dashboard
│
├── tests/              # Test suite
│   └── test_budget_manager.py
│
├── scripts/            # Utility scripts
│   └── seed_firestore.py # Initialize Firestore collections
│
├── legacy/             # Deprecated files (can be removed)
│   ├── bot_handler.py
│   ├── adaptive_cards.py
│   └── function_app.py
│
└── [config files]      # .env, firebase.json, requirements.txt, etc.
```

**Note**: Backend files use relative imports (e.g., `from .firebase_client import FirebaseClient`). External scripts/tests import using `from backend.module import ...`.

## Architecture

### Core Components

**FastAPI Backend** (`backend/api.py`)
- `/twilio/webhook` - Receives SMS/MMS from Twilio, processes expense, saves to Firestore, responds via SMS
- `/streamlit/process` - Receives voice/image from Streamlit UI, processes and saves
- `/health` - Health check endpoint

**Streamlit Frontend** (`frontend/app.py`)
- **Chat Interface (Default)**: SMS-like chat for quick expense entry with text and/or images
- Voice recording interface with audio upload to Firebase Storage
- Manual expense entry form with optional receipt image upload
- Budget dashboard with real-time progress bars and category breakdown
- Expense history table with filters and CSV export
- Runs on localhost (eventually web-deployed)

**Expense Parser** (`backend/expense_parser.py`)
- Handles three input types: text, images, voice transcriptions
- Uses OpenAI GPT-4 Vision for receipt images
- Uses OpenAI GPT for text/transcription parsing
- Extracts: expense_name, amount, date, category

**Data Schemas** (`backend/output_schemas.py`)
- `Expense`: Main expense model with fields:
  - `expense_name` (str) - Auto-generated descriptive name
  - `amount` (float)
  - `date` (Date) - Supports natural language like "yesterday", "last Tuesday"
  - `category` (ExpenseType enum)
- `ExpenseType` enum: FOOD_OUT, RENT, UTILITIES, MEDICAL, GAS, GROCERIES, RIDE_SHARE, COFFEE, HOTEL, TECH, TRAVEL, OTHER
- `Date`: day, month, year

**Firebase Integration** (`backend/firebase_client.py`)
- Firestore collections:
  - `expenses/` - Flat structure with timestamp filters
  - `budget_caps/` - Per-category monthly caps + total monthly cap
  - `categories/` - Enum key and value for each category
- Firebase Storage: Audio recordings from Streamlit UI

**Twilio Integration** (`backend/twilio_handler.py`)
- Webhook handler for incoming SMS/MMS
- Image download from Twilio
- SMS response sender with budget warnings

**Budget Manager** (`backend/budget_manager.py`)
- Budget calculation logic
- Warning message generation at 50%, 90%, 95%, 100%+ thresholds

**OpenAI Clients** (`backend/endpoints.py`)
- Standard OpenAI API configuration
- Supports GPT-4 Vision, GPT text processing, and Whisper transcription

### Data Flow

**SMS/MMS Flow (Twilio)**:
1. User texts expense → Twilio webhook → FastAPI `/twilio/webhook`
2. Download image if MMS, extract text
3. Parse with OpenAI (vision for image, GPT for text)
4. Save to Firestore `expenses/` collection
5. Check budget status (calculate % used for category and total)
6. Respond via SMS with confirmation + budget warnings
7. Example response: `✅ Saved $15 Chipotle lunch (FOOD_OUT) ⚠️ 90% of monthly budget used`

**Voice Recording Flow (Streamlit)**:
1. User records audio → Upload to Firebase Storage
2. Transcribe with OpenAI Whisper
3. Treat transcription as text input → Parse with OpenAI GPT
4. Save to Firestore `expenses/` collection
5. Display confirmation in Streamlit UI with budget status

**Input Format Flexibility**:
- Text can be anything: `"Chipotle lunch $15"`, `"spent $15 at chipotle for lunch"`, free-form (max 2 sentences)
- Images: Receipt photos processed with GPT-4 Vision
- Voice: Natural speech like "Starbucks coffee 5 dollars yesterday"
- Can receive 1-2 inputs at once (e.g., text + image, voice + image)
- Date defaults to today if not specified; supports natural language ("yesterday", "last Tuesday")

## Common Commands

### Local Development
```bash
# Start FastAPI backend
uvicorn backend.api:app --reload --port 8000

# Start Streamlit UI (separate terminal)
streamlit run frontend/app.py
```

### Testing
```bash
# Run budget manager tests
python tests/test_budget_manager.py

# Seed Firestore with categories and budget caps
python scripts/seed_firestore.py
```

Manual testing via:
- Twilio webhook testing (use ngrok for local testing)
- Streamlit UI on localhost

### Deployment (Future)
```bash
# Deploy to Google Cloud Functions
gcloud functions deploy expense-tracker --runtime python311 --trigger-http
```

## Budget Management

### Budget Cap Structure (Firestore `budget_caps/`)
- Per-category monthly caps (e.g., `FOOD_OUT: $500/month`)
- Total monthly spending cap
- Both stored in `budget_caps/` collection

### Budget Warnings
- Alert at **50%, 90%, 95%, 100%** of budget
- **Category budgets**: Warn EVERY TIME at thresholds (50%, 90%, 95%, 100%+)
- **Overall budget**: Warn ONCE per threshold (50%, 90%, 95%, 100%)
  - After crossing 100%, warn EVERY TIME
  - Tracking stored in `budget_alert_tracking/` collection
- Include in SMS responses and Streamlit UI

Example responses:
- `✅ Saved $50 Groceries (GROCERIES) ℹ️ 50% of GROCERIES budget used` (category warning - repeats)
- `✅ Saved $15 Coffee (COFFEE) ℹ️ 55% of monthly total budget used` (overall warning - one-time)
- `✅ Saved $200 Rent (RENT) 🚨 OVER BUDGET! 105% of monthly total budget used` (over 100% - repeats)

## Firebase Schema

### Collections

**`expenses/`** (flat structure)
```javascript
{
  expense_id: auto-generated,
  expense_name: "Chipotle lunch",
  amount: 15.00,
  date: { day: 26, month: 12, year: 2025 },
  category: "FOOD_OUT", // ExpenseType enum value
  timestamp: Firebase timestamp,
  input_type: "sms" | "voice" | "image" | "text", // for analytics
  // NO participants or project_name fields
}
```

**`budget_caps/`**
```javascript
{
  category: "FOOD_OUT", // or "TOTAL" for overall cap
  monthly_cap: 500.00,
  last_updated: Firebase timestamp
}
```

**`categories/`**
```javascript
{
  category_id: "FOOD_OUT", // ExpenseType enum key
  display_value: "dinner/lunch/breakfast/snacks, etc at a restaurant. Does NOT include coffee shops or buying coffee", // enum value
  emoji: "🍽️" // optional
}
```

**`recurring_expenses/`** (recurring expense templates)
```javascript
{
  template_id: auto-generated,
  expense_name: "Rent",
  amount: 1400.00,
  category: "RENT", // ExpenseType enum key
  frequency: "monthly" | "weekly" | "biweekly",
  day_of_month: 1, // for monthly (1-31)
  day_of_week: 0, // for weekly/biweekly (0=Monday, 6=Sunday)
  last_of_month: false, // true if user said "last day of month"
  last_reminded: { day, month, year }, // when pending expense was last created
  last_user_action: { day, month, year }, // when user last confirmed/skipped
  active: true, // false if deleted/paused
  created_at: Firebase timestamp
}
```

**`pending_expenses/`** (awaiting user confirmation)
```javascript
{
  pending_id: auto-generated,
  template_id: "ref_to_recurring_expense",
  expense_name: "Rent",
  amount: 1400.00,
  date: { day, month, year }, // when expense is due
  category: "RENT",
  sms_sent: true, // whether SMS was sent (for SMS flow)
  awaiting_confirmation: true, // false after user responds
  created_at: Firebase timestamp
}
```

**`budget_alert_tracking/`** (tracks which overall budget thresholds have been warned about)
```javascript
{
  // Document ID: "{year}-{month:02d}" (e.g., "2025-12")
  thresholds_warned: [50, 90], // List of thresholds already alerted (50, 90, 95, or 100)
  last_updated: Firebase timestamp
}
```

### Firebase Storage
- Audio recordings: `audio_recordings/{timestamp}_{user_id}.webm`

## Recurring Expenses Feature

### Overview
Users can create recurring expenses (rent, subscriptions, bills) that automatically generate pending confirmations each period. The system uses an auto-create with confirmation flow - expenses are created on schedule and await user approval before saving to the main expenses collection.

### Creating Recurring Expenses

**Via Streamlit Chat:**
- User types natural language with recurring keywords: `"recurring rent $1400 monthly on the 1st"`
- AI detects recurring intent (keywords: recurring, recur, subscription, monthly, weekly, biweekly)
- System creates template in `recurring_expenses/` collection
- If trigger date already passed, creates pending expense immediately
- User sees: `"✅ Created recurring Rent expense. Pending confirmation for 12/1/2025 - check Dashboard!"`

**Via SMS (Future):**
- Same detection logic as Streamlit
- Sends confirmation SMS before creating template
- User replies YES to create, NO to cancel
- If retroactive, sends pending confirmation immediately after creation

**Supported Formats:**
- `"recurring rent $1400 monthly on the 1st"`
- `"netflix subscription $15 monthly"` (infers today's day)
- `"gym $50 every month on the 15th"`
- `"groceries $200 weekly on Mondays"`
- `"phone bill $100 biweekly on Fridays"`
- `"rent 1500 monthly last day"` (last day of month)

### Trigger Logic

**On API Startup (Pre-Cloud Functions):**
```python
For each active recurring_expense:
    trigger_time = calculate_most_recent_trigger_date(recurring_expense)

    if last_reminded < trigger_time:
        # Create pending expense
        create_pending_expense()
        update last_reminded = today

    elif last_reminded >= trigger_time AND last_user_action > last_reminded:
        # User already handled it
        pass

    elif last_reminded >= trigger_time AND last_user_action < last_reminded:
        # Still pending in Streamlit
        show_in_dashboard()
```

**Post-Cloud Functions Migration:**
- Cloud Scheduler runs daily at midnight
- Calls `/admin/check-recurring` endpoint
- Same logic as above
- **TODO**: When deploying to Cloud Functions, change from "on startup" to "daily scheduled job"

### Confirmation Flow

**Streamlit Dashboard:**
1. Dashboard shows pending expenses section at top
2. Each pending shows: Name, Amount, Category, Due Date
3. User clicks "✅ Confirm" → Saves to `expenses/`, deletes from `pending_expenses/`, updates `last_user_action`
4. User clicks "⏭️ Skip" → Deletes from `pending_expenses/`, updates `last_user_action`

**SMS Flow (Future):**
1. System sends: `"Rent $1400 due 12/1. Reply YES to confirm, SKIP to skip, or CANCEL to stop recurring"`
2. User replies:
   - **YES** → Confirms expense
   - **YES $1050** → Confirms with adjusted amount
   - **SKIP** → Skips this occurrence
   - **CANCEL** → Asks double-confirmation → **DELETE** → Deletes recurring template
3. After confirmation, if more pending exist, sends next one
4. Non-confirmation text → Processes as regular expense, then re-sends pending confirmation

### Recurring Templates Management

**Streamlit "Recurring" Tab:**
- Shows all recurring templates (active and inactive)
- Displays: Name, Amount, Frequency, Category, Last Triggered, Status
- Actions:
  - **Delete** (🗑️) → Marks `active=false`
  - Toggle "Show Inactive" to view paused/deleted templates

**Features:**
- Monthly: Specific day (1-31) or "last day of month"
- Weekly: Specific day of week (Monday-Sunday)
- Biweekly: Every 2 weeks on specific day
- "Last day of month" handling: If day is 31 and it's February, uses last day (28/29)

### Budget Projections

**Dashboard "Projected Budget" Section:**
- **Current Spending**: Only confirmed expenses from `expenses/` collection
- **Projected Spending**: Current + all active recurring templates
- Shows side-by-side comparison
- Lists categories with projected increases
- Helps users see budget impact before recurring expenses are confirmed

Example:
```
Current Spending: $1,200 / $2,000 (60%)
Projected Spending: $2,600 / $2,000 (130%)
   (includes $1,400 in recurring expenses)

Categories with Recurring Expenses:
🏠 RENT: Current: $0 → Projected: $1,400 (93%)
💻 TECH: Current: $15 → Projected: $30 (30%)
```

### API Endpoints

**Recurring Endpoints:**
- `GET /recurring` - Get all recurring expense templates
- `DELETE /recurring/{template_id}` - Delete/deactivate template
- `GET /pending` - Get all pending expenses
- `POST /pending/{pending_id}/confirm` - Confirm pending (optional `adjusted_amount`)
- `DELETE /pending/{pending_id}` - Skip/delete pending

### State Management Fields

**`last_reminded`**: When system last created a pending expense for this template
**`last_user_action`**: When user last confirmed/skipped/deleted a pending expense

**These fields prevent duplicates:**
- If `last_reminded >= trigger_date AND last_user_action > last_reminded` → Already handled
- If `last_reminded >= trigger_date AND last_user_action < last_reminded` → Still pending
- If `last_reminded < trigger_date` → Create new pending

### Edge Cases Handled

1. **Retroactive Creation**: If user creates "monthly on 1st" on Dec 15, immediately creates pending for Dec 1
2. **Day Overflow**: If recurring is "31st" and it's February, triggers on Feb 28/29
3. **Multiple Pending Same Day**: Sequential confirmation in SMS, all shown at once in Streamlit
4. **API Restart**: Won't create duplicates due to `last_reminded` check
5. **Pending Without Action**: Stays in Streamlit until user confirms/skips (no timeout)

## Key Implementation Notes

### Removed Fields
The following fields from the original Teams bot schema are **NOT USED** for personal expenses:
- `participants` - Only needed for business expense splitting
- `project_name` - Only needed for business project tracking

### Category Consistency
When modifying categories, ensure consistency across:
1. `ExpenseType` enum in `output_schemas.py`
2. AI prompts in `expense_parser.py`
3. Category mapping logic
4. Firestore `categories/` collection
5. Budget cap configuration

### Natural Language Date Processing
AI should parse dates like:
- "yesterday" → today - 1 day
- "last Tuesday" → most recent Tuesday
- "12/25" → December 25, current year
- No date specified → assume today

### Input Type Handling
The parser must handle:
1. **Text only**: `"Coffee $5"` → AI infers category, generates name
2. **Image only**: Receipt photo → OCR + AI extraction
3. **Text + Image**: Use text as context for image parsing
4. **Voice transcription**: Treat as text input after Whisper processing

### Multi-Input Processing
When receiving multiple inputs (e.g., text caption + image):
- Use text as additional context for the AI
- Prioritize image data for amount/merchant if both present
- Merge information intelligently (don't duplicate)

## Development Status

### Completed
- ✅ Backend directory structure with all core modules
- ✅ Firebase integration (Firestore + Storage)
- ✅ Twilio webhook handling and SMS responses
- ✅ Budget management with threshold warnings
- ✅ Expense parsing (text and image support)
- ✅ Streamlit UI with chat interface, dashboard, and history
- ✅ Chat interface mirrors SMS experience (supports text and images)
- ✅ Test suite for budget manager

### Legacy Files (can be deleted)
- `legacy/function_app.py` - Azure Functions entry point (not needed)
- `legacy/bot_handler.py` - Teams Bot Framework handler (not needed)
- `legacy/adaptive_cards.py` - Teams Adaptive Cards (not needed)

### Future Enhancements
- Voice transcription with Whisper API
- Enhanced Streamlit UI features
- Additional test coverage
- Deployment automation

## Testing Considerations

### Twilio Local Testing
- Use ngrok to expose localhost FastAPI to Twilio webhooks
- Set Twilio webhook URL to `https://<ngrok-url>/twilio/webhook`

### Firestore Emulator (Optional)
```bash
firebase emulators:start --only firestore
```

### Budget Threshold Testing
Test all warning levels:
- 49% → no warning
- 50% → ℹ️ warning
- 90% → ⚠️ warning
- 95% → ⚠️ warning
- 100%+ → 🚨 OVER BUDGET warning

---

## MCP Migration (In Progress)

### Overview
The app is migrating from OpenAI API to **MCP (Model Context Protocol)** architecture using Claude API and a custom MCP client. This migration enables **conversational expense management** via SMS, where users can edit, delete, and query expenses using natural language.

### Migration Strategy

**Dual-Backend Approach**: Both OpenAI and MCP backends will run in parallel during development and testing. The existing OpenAI backend will remain functional until MCP is fully tested and stable. Only then will we switch to MCP as the primary backend.

**Why MCP?**
- **Conversational SMS**: Enable multi-turn conversations for editing expenses ("Actually that was $6, not $5")
- **Full CRUD Operations**: Delete, update, search expenses via natural language
- **Analytics Queries**: "How much did I spend on food last week?"
- **Tool Orchestration**: Claude decides which Firebase operations to call based on user intent
- **Better Context Handling**: Maintain conversation history to understand "that expense", "last one", etc.

### Architecture Comparison

#### Current Architecture (OpenAI)
```
SMS Text → Twilio Webhook
          ↓
    FastAPI /twilio/webhook
          ↓
    expense_parser.py (OpenAI GPT-4)
          ↓
    firebase_client.py (Direct Firebase calls)
          ↓
    Firebase Firestore
```

#### Target Architecture (MCP)
```
SMS Text → Twilio Webhook
          ↓
    FastAPI /twilio/webhook-mcp (new endpoint)
          ↓
    backend/mcp/client.py (Custom MCP Client)
          ↓
    Claude API (Anthropic)
          ↓
    backend/mcp/expense_server.py (MCP Server with tools)
          ↓
    Firebase Firestore
```

#### During Migration (Dual Backend)
```
SMS → Twilio → FastAPI
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
   OpenAI Backend    MCP Backend
   /twilio/webhook   /twilio/webhook-mcp
   (EXISTING)        (IN DEVELOPMENT)
        ↓                 ↓
      Firebase        Firebase
```

**Feature Flag**: `USE_MCP_BACKEND` (default: `false`) controls which backend processes requests.

### New Capabilities with MCP

**Create Expenses** (same as OpenAI):
- "Starbucks $5"
- "Chipotle lunch $15 yesterday"
- Photo of receipt (MMS)

**Edit/Update** (new):
- "Actually that coffee was $6, not $5"
- "Change yesterday's lunch to GROCERIES category"
- "Update my rent payment to $1450"

**Delete** (new):
- "Delete that last coffee expense"
- "Remove the duplicate Chipotle charge"

**Query/Search** (new):
- "How much did I spend on food last week?"
- "Show me all my Uber expenses in December"
- "What was my biggest restaurant expense this month?"

**Budget Questions** (new):
- "How much of my food budget is left?"
- "Am I over budget in any categories?"

**Analytics** (new):
- "What's my average daily spending?"
- "Compare this month's food spending to last month"

### MCP Server Tools

The expense MCP server (`backend/mcp/expense_server.py`) exposes Firebase operations as tools:

**Basic Tools** (Phase 1):
- `save_expense(name, amount, date, category)` - Create new expense
- `get_budget_status(category?)` - Check budget status
- `get_categories()` - List valid expense categories

**CRUD Tools** (Phase 3):
- `update_expense(expense_id, name?, amount?, date?, category?)` - Edit expense
- `delete_expense(expense_id)` - Remove expense
- `get_expense_by_id(expense_id)` - Fetch single expense
- `get_recent_expenses(limit?, category?)` - Last N expenses
- `search_expenses(text_query)` - Fuzzy search by name

**Analytics Tools** (Phase 4):
- `query_expenses(category?, start_date?, end_date?, limit?)` - Flexible filtering
- `get_spending_by_category(start_date?, end_date?)` - Category breakdown
- `get_spending_summary(start_date?, end_date?)` - Total + average
- `get_budget_remaining(category?)` - Budget left in category
- `compare_periods(...)` - Month-over-month comparisons

### Conversation State Management

**Architecture**: Uses **in-memory cache** (Python dict) instead of Firestore for short-term context
- Single user system (for now)
- Tracks last 5 expenses for "actually that was..." and "delete that" references
- Lost on API restart, but acceptable for local dev
- Future: Migrate to Redis when scaling to multiple users

**In-Memory Cache Structure** (`backend/mcp/conversation_cache.py`):
```python
{
    "+1234567890": {  # phone_number key
        "last_expense_id": "abc123",  # Most recent expense
        "recent_expenses": ["abc123", "def456", "ghi789"],  // Last 5
        "last_updated": datetime(2025, 12, 30, 10, 30, 0)
    }
}
```

**Conversation Cache** (`backend/mcp/conversation_cache.py`):
- Tracks last 5 expense IDs per phone number
- Auto-cleanup for entries older than 24 hours (manual trigger)
- Supports "that", "last one" references in SMS
- Fast lookups (<1ms) for context-aware edits

### File Structure (MCP Components)

**New Files**:
```
backend/
├── mcp/
│   ├── __init__.py
│   ├── expense_server.py      # MCP server with expense tools
│   ├── client.py              # Wrapper around custom MCP client
│   └── conversation_cache.py  # In-memory conversation state cache
```

**Modified Files**:
- `backend/api.py` - Add `/twilio/webhook-mcp` endpoint
- `frontend/app.py` - (Optional) Update chat to use MCP backend

**Preserved (Not Modified)**:
- `backend/firebase_client.py` - MCP tools call these methods
- `backend/budget_manager.py` - MCP tools call these methods
- `backend/recurring_manager.py` - No changes
- `backend/expense_parser.py` - Kept for OpenAI backend, archived after cutover
- `backend/endpoints.py` - Kept for OpenAI backend, archived after cutover

### Environment Variables (MCP)

Add to `.env`:
```bash
# Anthropic/Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Feature Flags
USE_MCP_BACKEND=false  # Set to true after testing complete
```

**Note**: Conversation cache settings (TTL, size limits) are hardcoded in `conversation_cache.py` since it's in-memory and single-user.

### Migration Phases

See `build_plan.md` Phase 4 for detailed implementation plan:

1. **Phase 1: Basic MCP Infrastructure** - Replace parsing with MCP, maintain parity with OpenAI
2. **Phase 2: Conversation State** - Enable multi-turn conversations
3. **Phase 3: CRUD Tools** - Add edit/delete capabilities
4. **Phase 4: Analytics Tools** - Add query/analytics capabilities
5. **Phase 5: Streamlit Migration** (Optional) - Migrate Streamlit chat to MCP
6. **Phase 6: Cutover** - Switch to MCP, archive OpenAI code

**Estimated Timeline**: 4-6 weeks (part-time development)

### Rollback Plan

If MCP has critical issues, we can immediately rollback:

1. Set `USE_MCP_BACKEND = False`
2. Route Twilio webhook to `/twilio/webhook` (OpenAI endpoint)
3. OpenAI code remains in codebase until MCP is stable

**Rollback Triggers**:
- Response time > 5 seconds (OpenAI typically < 2 seconds)
- Error rate > 5%
- Incorrect parsing > 10% of requests
- Budget warnings not working

### Testing Strategy

**Parallel Testing**:
- Both backends write to same Firebase collections
- Can switch between backends with feature flag
- Compare responses between OpenAI and MCP for same inputs
- Monitor error rates, response times, costs

**A/B Testing Capability**:
- Route specific phone numbers to MCP for testing
- Gradual rollout to production traffic
- Easy rollback if issues arise

### Important Notes for Development

**DO NOT DELETE OpenAI Code During Migration**:
- Keep `expense_parser.py` functional
- Keep `endpoints.py` functional
- Only move to `legacy/` after successful cutover
- Maintain ability to rollback quickly

**MCP Development Workflow**:
1. Build MCP components in `backend/mcp/`
2. Test with `/twilio/webhook-mcp` endpoint
3. Keep `/twilio/webhook` (OpenAI) as fallback
4. Only switch default after thorough testing

**Conversation Context**:
- MCP enables multi-turn conversations
- Claude remembers last 10 messages per phone number
- Can reference "that expense", "last coffee", etc.
- Conversations auto-expire after 24 hours

**Confirmation Flows**:
- Destructive actions (delete, large edits) require confirmation
- Claude shows what will be changed before confirming
- If ambiguous ("delete that"), Claude shows options
- System prompt enforces confirmation requirements

### Current Status

**Migration Status**: 🔵 In Progress (as of 2025-12-30)

**Phase 4.1 (Basic MCP Infrastructure)**: ✅ **COMPLETE** (2025-12-30)
- ✅ MCP server with stdio transport created
- ✅ Three tools implemented: `save_expense`, `get_budget_status`, `get_categories`
- ✅ FastAPI integration with `/twilio/webhook-mcp` endpoint
- ✅ Feature flag `USE_MCP_BACKEND` allows switching between OpenAI and MCP
- ✅ Text parsing tested: "Starbucks $5" → COFFEE, $5.00
- ✅ Image parsing tested: Jamba Juice receipt → $12.89, FOOD_OUT
- ✅ Budget warnings working: "ℹ️ 88% of COFFEE budget used ($6.00 left)"
- ✅ Both backends can run in parallel

**Files Created**:
- `backend/mcp/__init__.py`
- `backend/mcp/expense_server.py` (MCP server with tools)
- `backend/mcp/client.py` (FastAPI wrapper)
- `backend/system_prompts.py` (Centralized prompts)

**Files Modified**:
- `backend/api.py` (added MCP endpoint and startup logic)
- `mcp-client/client.py` (migrated to standard Anthropic SDK)
- `requirements.txt` (added anthropic>=0.18.0, mcp>=0.9.0)

**Next Phase**: Phase 4.2 (Conversation State Management) - Add in-memory cache for multi-turn conversations

See `build_plan.md` Phase 4 for detailed task checklist and progress tracking.
