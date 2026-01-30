# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A personal expense tracking and budgeting app with conversational AI capabilities powered by Claude + MCP (Model Context Protocol).

**Input Methods:**
- Web UI (React frontend)
- API endpoint for text/image/audio expense submission

**Core Features:**
- Natural language expense entry ("Coffee $5 yesterday")
- Receipt image parsing via Claude Vision
- Voice memo transcription via Whisper
- Conversational CRUD operations ("delete that last expense", "change it to $6")
- Budget tracking with threshold warnings (50%, 90%, 95%, 100%)
- Recurring expense management
- Analytics queries ("how much did I spend on food last week?")

All data is stored in Firebase Firestore.

## Environment Setup

Required environment variables in `.env` (DO NOT EDIT .env directly - ask user to update):
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude
- `FIREBASE_KEY` - Firebase service account key JSON (or path to key file)
- `OPENAI_API_KEY` - OpenAI API key (for Whisper audio transcription only)

**IMPORTANT**: Never attempt to edit `.env` file. Always ask the user to add/update environment variables.

Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
finance_bot/
├── backend/              # FastAPI backend and core logic
│   ├── api.py           # FastAPI app with endpoints
│   ├── firebase_client.py # Firestore/Storage operations
│   ├── budget_manager.py # Budget calculations & warnings
│   ├── recurring_manager.py # Recurring expense logic
│   ├── output_schemas.py # Pydantic data models
│   ├── system_prompts.py # Claude system prompts
│   ├── whisper_client.py # Audio transcription
│   └── mcp/             # MCP (Model Context Protocol) components
│       ├── __init__.py
│       ├── expense_server.py      # MCP server with 17 expense tools
│       ├── client.py              # MCP client wrapper
│       ├── conversation_cache.py  # In-memory conversation state
│       ├── server_config.py       # Server configuration
│       └── connection_manager.py  # Connection management
│
├── frontend/            # React frontend (Vite + TypeScript)
│   └── src/
│       ├── components/  # UI components (chat, layout, ui)
│       ├── contexts/    # React contexts (Auth, Server, Theme)
│       ├── hooks/       # Custom hooks
│       ├── pages/       # Page components (Chat, Dashboard, Expenses, Login)
│       ├── services/    # API services
│       └── types/       # TypeScript types
│
├── tests/              # Test suite
│   └── test_budget_manager.py
│
├── scripts/            # Utility scripts
│   └── seed_firestore.py # Initialize Firestore collections
│
├── legacy/             # Archived code (do not use)
│   ├── expense_parser.py  # Old OpenAI expense parsing
│   ├── endpoints.py       # Old OpenAI client config
│   └── twilio_handler.py  # Old Twilio SMS handling
│
└── [config files]      # .env, firebase.json, requirements.txt, etc.
```

**Note**: Backend files use relative imports (e.g., `from .firebase_client import FirebaseClient`). External scripts/tests import using `from backend.module import ...`.

## Architecture

### Core Components

**FastAPI Backend** (`backend/api.py`)
- `POST /mcp/process_expense` - Main endpoint for expense processing (text/image/audio)
- `POST /chat/stream` - Streaming chat with MCP tools (SSE)
- `GET /expenses` - Query expense history with filters
- `GET /budget` - Get current budget status
- `PUT /budget-caps/bulk-update` - Update all budget caps
- `GET /recurring` - Get recurring expense templates
- `GET /pending` - Get pending expenses awaiting confirmation
- `POST /pending/{id}/confirm` - Confirm a pending expense
- `DELETE /pending/{id}` - Skip/delete a pending expense
- `DELETE /recurring/{id}` - Delete a recurring template
- `POST /admin/check-recurring` - Trigger recurring expense check (for Cloud Scheduler)
- `GET /servers` - List available MCP servers
- `POST /connect/{server_id}` - Connect to an MCP server
- `GET /status` - Get MCP connection status
- `POST /disconnect` - Disconnect from MCP server
- `GET /health` - Health check

**MCP Server** (`backend/mcp/expense_server.py`)
The MCP server exposes 17 tools that Claude can call:

*Basic Tools:*
- `save_expense` - Create new expense
- `get_budget_status` - Check budget and get warnings
- `get_categories` - List valid expense categories

*CRUD Tools:*
- `update_expense` - Edit expense fields
- `delete_expense` - Remove expense
- `get_recent_expenses` - Get last N expenses
- `search_expenses` - Search by name

*Analytics Tools:*
- `query_expenses` - Filter by date/category/amount
- `get_spending_by_category` - Category breakdown
- `get_spending_summary` - Total, count, average
- `get_budget_remaining` - Budget status view
- `compare_periods` - Period comparison
- `get_largest_expenses` - Top expenses

*Recurring Tools:*
- `create_recurring_expense` - Create template
- `list_recurring_expenses` - List templates
- `delete_recurring_expense` - Delete template

**Data Schemas** (`backend/output_schemas.py`)
- `Expense`: expense_name, amount, date, category
- `ExpenseType` enum: FOOD_OUT, RENT, UTILITIES, MEDICAL, GAS, GROCERIES, RIDE_SHARE, COFFEE, HOTEL, TECH, TRAVEL, OTHER
- `RecurringExpense`: template for recurring expenses
- `PendingExpense`: expense awaiting confirmation

**Firebase Integration** (`backend/firebase_client.py`)
- Firestore collections: `expenses/`, `budget_caps/`, `categories/`, `recurring_expenses/`, `pending_expenses/`, `budget_alert_tracking/`

**Budget Manager** (`backend/budget_manager.py`)
- Budget calculation logic
- Warning generation at 50%, 90%, 95%, 100%+ thresholds

### Data Flow

```
User Input (text/image/audio)
          ↓
    FastAPI /mcp/process_expense
          ↓
    MCP Client (backend/mcp/client.py)
          ↓
    Claude API (Anthropic)
          ↓
    MCP Server Tools (backend/mcp/expense_server.py)
          ↓
    Firebase Firestore
          ↓
    Response with budget warnings
```

**Conversational Features:**
- Multi-turn conversations for editing ("Actually that was $6")
- Context tracking for "that expense", "last one" references
- Natural language queries ("how much did I spend on food?")

## Common Commands

### Local Development
```bash
# Start FastAPI backend
uvicorn backend.api:app --reload --port 8000
```

### Testing
```bash
# Run budget manager tests
python tests/test_budget_manager.py

# Seed Firestore with categories and budget caps
python scripts/seed_firestore.py
```

### Deployment
The app is deployed on **Google Cloud Run**.

### Cloud Scheduler Setup (Recurring Expenses)

To run recurring expense checks daily:

**1. Add environment variables to Cloud Run:**
```bash
ADMIN_API_KEY=<generate-a-secure-random-key>
SKIP_STARTUP_RECURRING_CHECK=true
```

**2. Create Cloud Scheduler job:**
```bash
gcloud scheduler jobs create http check-recurring-expenses \
  --location=us-central1 \
  --schedule="0 6 * * *" \
  --uri="https://<your-cloud-run-url>/admin/check-recurring" \
  --http-method=POST \
  --headers="X-API-Key=<your-admin-api-key>" \
  --time-zone="America/Chicago"
```

## Budget Management

### Budget Warnings
- Alert at **50%, 90%, 95%, 100%** of budget
- **Category budgets**: Warn EVERY TIME at thresholds
- **Overall budget**: Warn ONCE per threshold (except 100%+ which repeats)
- Tracking stored in `budget_alert_tracking/` collection

## Firebase Schema

### Collections

**`expenses/`**
```javascript
{
  expense_id: auto-generated,
  expense_name: "Chipotle lunch",
  amount: 15.00,
  date: { day: 26, month: 12, year: 2025 },
  category: "FOOD_OUT",
  timestamp: Firebase timestamp,
  input_type: "mcp" | "recurring"
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

**`recurring_expenses/`**
```javascript
{
  template_id: auto-generated,
  expense_name: "Rent",
  amount: 1400.00,
  category: "RENT",
  frequency: "monthly" | "weekly" | "biweekly",
  day_of_month: 1,
  day_of_week: null,
  last_of_month: false,
  last_reminded: { day, month, year },
  last_user_action: { day, month, year },
  active: true,
  created_at: Firebase timestamp
}
```

**`pending_expenses/`**
```javascript
{
  pending_id: auto-generated,
  template_id: "ref_to_recurring_expense",
  expense_name: "Rent",
  amount: 1400.00,
  date: { day, month, year },
  category: "RENT",
  awaiting_confirmation: true,
  created_at: Firebase timestamp
}
```

## Key Implementation Notes

### Category Consistency
When modifying categories, ensure consistency across:
1. `ExpenseType` enum in `output_schemas.py`
2. MCP server tools in `expense_server.py`
3. System prompts in `system_prompts.py`
4. Firestore `categories/` collection
5. Budget cap configuration

### MCP Conversation Context
- In-memory cache tracks last 5 expenses per session
- Supports "that expense", "delete that", "the second one" references
- 24-hour TTL auto-cleanup
- Future: Migrate to Redis for multi-user support

### Input Type Handling
The MCP server handles:
1. **Text only**: `"Coffee $5"` → Claude infers category, generates name
2. **Image only**: Receipt photo → Claude Vision extraction
3. **Text + Image**: Use text as context for image parsing
4. **Audio**: Transcribed via Whisper, then processed as text

## Development Roadmap

### Completed
- ✅ MCP architecture with Claude
- ✅ 17 expense management tools
- ✅ Conversational CRUD operations
- ✅ Analytics and query tools
- ✅ Recurring expense management
- ✅ Budget tracking with warnings
- ✅ Image parsing via Claude Vision
- ✅ Audio transcription via Whisper
- ✅ React frontend with chat, dashboard, and expense management

### Future
- 🔄 Multi-user support (migrate conversation cache to Redis)

### Legacy (Archived)
The following have been moved to `legacy/` and are no longer used:
- OpenAI expense parsing
- Old Twilio SMS handling

## Testing

### Budget Threshold Testing
Test all warning levels:
- 49% → no warning
- 50% → ℹ️ warning
- 90% → ⚠️ warning
- 95% → ⚠️ warning
- 100%+ → 🚨 OVER BUDGET warning

### Firestore Emulator (Optional)
```bash
firebase emulators:start --only firestore
```
