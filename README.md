# Budget Master

A personal expense tracking and budgeting app with conversational AI capabilities powered by Claude + MCP (Model Context Protocol). Features a React web UI and FastAPI backend, all backed by Firebase.

## What this repo contains

- **FastAPI backend** for expense processing, analytics, and MCP chat endpoints.
- **React frontend** with chat interface, dashboard, and expense management.
- **Firebase integration** for Firestore data + Storage for audio uploads.
- **MCP architecture** with Claude-driven tools for conversational expense CRUD + analytics.

## Key features

- **Multi-input expense capture**: text, receipt images (Claude Vision), and voice transcription (Whisper).
- **Automatic parsing**: merchant/amount/date/category extraction via Claude.
- **Budget tracking**: category + overall caps with threshold warnings (50/90/95/100%).
- **Recurring expenses**: templates, pending confirmations, and projection views.
- **Conversational management**: natural language to edit, delete, query, and analyze expenses ("delete that last expense", "how much did I spend on food last week?").

## Architecture overview

### Primary runtime services
- **FastAPI** (`backend/api.py`): expense processing, budgets, and MCP chat APIs.
- **React UI** (`frontend/`): chat interface, dashboard, and expense management.
- **Firebase**: Firestore collections for expenses/budgets + Storage for audio.
- **MCP Server** (`backend/mcp/`): 17 expense management tools powered by Claude.

## Repository layout

```
backend/                 FastAPI backend, Firebase client, MCP tools
frontend/                React UI (Vite + TypeScript)
tests/                   Budget manager tests
scripts/                 Seed and maintenance scripts
docs/                    Build plan and migration docs
legacy/                  Archived OpenAI code (not used)
CLAUDE.md                Canonical repo guidance and architecture notes
```

## Environment configuration

Create a `.env` file (do **not** edit one committed to the repo) with the following keys:

```bash
# Claude API (expense parsing and chat)
ANTHROPIC_API_KEY=

# Firebase
FIREBASE_KEY=

# OpenAI (Whisper audio transcription only)
OPENAI_API_KEY=
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Local development

### Start the backend
```bash
uvicorn backend.api:app --reload --port 8000
```

### Start the React frontend
```bash
cd frontend && npm run dev
```

### Run tests
```bash
python tests/test_budget_manager.py
```

### Seed Firestore
```bash
python scripts/seed_firestore.py
```

## Frontend (React)

The React app (`frontend/`) provides the main web interface:

- **Chat page**: Conversational expense entry with text, image upload, and voice recording. Supports natural language commands for creating, editing, deleting, and querying expenses.
- **Dashboard page**: Budget summaries, category progress bars, and spending analytics.
- **Expenses page**: Filterable expense history with search and management.
- **Login page**: Authentication via Firebase.

## Execution flows

### Text/image expense entry
1. User submits text and/or image from the React chat interface.
2. Frontend calls `POST /chat/stream` with content payloads.
3. MCP client sends to Claude API with expense tools.
4. Claude calls appropriate MCP tools (save_expense, get_budget_status, etc.).
5. Expense is saved to Firestore and response streamed back to UI.

### Voice expense entry
1. User records audio from the React chat interface.
2. Audio is transcribed via Whisper API.
3. Transcription is processed as text through the MCP flow.
4. Expense is saved to Firestore and response returned.

### Conversational edits/queries
1. User sends a natural language command (e.g., "Actually make that $6", "How much did I spend on food?").
2. MCP client uses conversation cache + Claude to interpret intent.
3. Claude calls appropriate tools (update_expense, query_expenses, etc.).
4. Response summarizes the change or query results.

## API surface

### Core endpoints
- `POST /mcp/process_expense` — Main expense processing (text/image/audio)
- `POST /chat/stream` — Streaming chat with MCP tools (SSE)
- `GET /expenses` — Filtered expense list
- `GET /budget` — Budget caps + summaries
- `PUT /budget-caps/bulk-update` — Update budget caps
- `GET /recurring` — Recurring expense templates
- `GET /pending` — Pending expenses awaiting confirmation
- `POST /pending/{id}/confirm` — Confirm a pending expense
- `DELETE /pending/{id}` — Skip/delete a pending expense

### MCP server endpoints
- `GET /servers` — List available MCP servers
- `POST /connect/{server_id}` — Connect to an MCP server
- `GET /status` — Get MCP connection status
- `POST /disconnect` — Disconnect from MCP server

## Data model (Firestore)

Primary collections:
- `expenses/` — flattened expenses (name, amount, date, category, timestamp)
- `budget_caps/` — per-category + total monthly caps
- `categories/` — category metadata
- `recurring_expenses/` — recurring templates
- `pending_expenses/` — awaiting confirmation
- `budget_alert_tracking/` — threshold notifications for overall budget

## MCP tool surface (high level)

The MCP server (`backend/mcp/expense_server.py`) exposes tools for:
- **Create**: `save_expense`
- **Update/Delete**: `update_expense`, `delete_expense`
- **Lookup**: `get_recent_expenses`, `search_expenses`, `query_expenses`
- **Analytics**: `get_spending_summary`, `get_spending_by_category`, `compare_periods`
- **Budgets**: `get_budget_status`, `get_budget_remaining`
- **Recurring**: `create_recurring_expense`, `list_recurring_expenses`, `delete_recurring_expense`

## Status

MCP backend is **complete** with full CRUD, analytics, and recurring expense support. The React frontend provides chat, dashboard, and expense management interfaces. See `CLAUDE.md` for architecture details.

## Notes

- **Legacy code** in `legacy/` folder is archived for reference but not used.
- **MCP architecture** uses Claude for all expense parsing and conversational features.
- **Deployment** is configured for Google Cloud Run (see Dockerfile).

## Related docs

- `CLAUDE.md` — comprehensive architecture and design notes
- `docs/build_plan.md` — development history and migration notes
