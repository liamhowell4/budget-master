# Budget Master

A personal expense tracking + budgeting system with SMS/MMS ingestion (Twilio), a Streamlit web UI, and a FastAPI backend backed by Firebase. The project is mid-migration from OpenAI parsing to a Claude + MCP architecture that enables conversational expense management (edit/delete/query) over SMS.

## What this repo contains

- **FastAPI backend** for SMS/MMS webhooks, Streamlit requests, analytics, and MCP chat endpoints.
- **Streamlit frontend** with chat-like entry, dashboards, and history export.
- **Firebase integration** for Firestore data + Storage for audio uploads.
- **MCP migration** that adds Claude-driven tools for CRUD + analytics over expenses.

## Key features

- **Multi-input expense capture**: SMS text, MMS receipt images, Streamlit text/image, and voice transcription.
- **Automatic parsing**: merchant/amount/date/category extraction with LLMs.
- **Budget tracking**: category + overall caps with threshold warnings (50/90/95/100%).
- **Recurring expenses**: templates, pending confirmations, and projection views.
- **Conversational management (MCP)**: edit, delete, query, and analyze expenses via SMS.

## Architecture overview

### Primary runtime services
- **FastAPI** (`backend/api.py`): Twilio webhook endpoints, Streamlit processing, budgets, and MCP chat APIs.
- **Streamlit UI** (`frontend/app.py`): interactive dashboard + expense entry.
- **Firebase**: Firestore collections for expenses/budgets + Storage for audio.

### OpenAI vs MCP backends
The code currently supports **dual backends**:
- **OpenAI backend** (`backend/expense_parser.py`, `backend/endpoints.py`)
- **MCP backend** (`backend/mcp/` + `backend/system_prompts.py`)

A feature flag `USE_MCP_BACKEND` determines which path is used for SMS processing.

## Repository layout

```
backend/                 FastAPI backend, parsers, Firebase, MCP tools
frontend/                Streamlit UI
tests/                   Budget manager tests
scripts/                 Seed and maintenance scripts
docs/                    Build plan and migration docs
BACKEND_API_CONTRACT.md  MCP chat frontend contract
CLAUDE.md                Canonical repo guidance and architecture notes
```

## Environment configuration

Create a `.env` file (do **not** edit one committed to the repo) with the following keys:

```bash
# OpenAI (legacy parsing + Whisper)
OPENAI_API_KEY=

# Firebase
FIREBASE_KEY=

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_ACCOUNT_TOKEN=
TWILIO_SECRET_SID=
TWILIO_SECRET_KEY=

# MCP migration
ANTHROPIC_API_KEY=
USE_MCP_BACKEND=false
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

### Start the Streamlit UI
```bash
streamlit run frontend/app.py
```

### Run tests
```bash
python tests/test_budget_manager.py
```

### Seed Firestore
```bash
python scripts/seed_firestore.py
```

## Frontend behavior (Streamlit)

The Streamlit app (`frontend/app.py`) is the primary desktop/web UI and mirrors much of the SMS flow. Key UI areas and behaviors:

- **Chat-like expense entry**: A conversational input area that accepts free-form text and optional receipt images. Submissions call the backend to parse and save expenses.
- **Manual entry form**: Structured inputs for name/amount/date/category, plus optional image upload.
- **Voice capture**: Audio upload is supported (stored in Firebase) and intended for transcription-based entry.
- **Dashboard view**: Budget summaries, category progress bars, and warnings at key thresholds.
- **History view**: Filterable table of expenses with CSV export.
- **Recurring tab**: Shows templates and pending confirmations for recurring expenses.

The Streamlit UI is currently tied to the OpenAI parsing flow for chat-style entry; the MCP migration includes a future task to route Streamlit chat to MCP for editing/deleting/querying expenses.

## Execution flows

### 1) SMS/MMS expense capture (Twilio)
1. User sends an SMS or MMS receipt to the Twilio number.
2. Twilio posts to `POST /twilio/webhook` (OpenAI) or `POST /twilio/webhook-mcp` (MCP).
3. Backend downloads media (if present) and parses the message/image.
4. Expense is saved to Firestore (`expenses/`).
5. Budget warnings are computed and returned via SMS.

### 2) Streamlit text/image entry
1. User submits text and/or image from the Streamlit UI.
2. Streamlit calls `POST /streamlit/process` with content payloads.
3. Backend parses inputs and saves expense to Firestore.
4. Streamlit renders the confirmation and updated budget summary.

### 3) Streamlit voice entry
1. User uploads audio from the Streamlit UI.
2. Audio is stored in Firebase Storage.
3. Backend transcribes audio (Whisper path) and parses the transcription.
4. Expense is saved to Firestore and returned to the UI.

### 4) MCP conversational edits/queries (SMS)
1. User sends a natural language edit/query (e.g., “Actually make that $6”).
2. MCP backend uses conversation cache + tools to update/query Firestore.
3. Response summarizes the change or query results via SMS.

## API surface

### Core backend endpoints
- `POST /twilio/webhook` — OpenAI-backed SMS/MMS ingestion
- `POST /twilio/webhook-mcp` — MCP-backed SMS/MMS ingestion
- `POST /streamlit/process` — Streamlit input processing
- `GET /expenses` — filtered expense list
- `GET /budget` — budget caps + summaries

### MCP chat endpoints
The MCP chat endpoints are documented in `BACKEND_API_CONTRACT.md` and include:
- `GET /servers`
- `POST /connect/{server_id}`
- `GET /status`
- `POST /disconnect`
- `POST /chat/stream`

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

## Migration status (MCP)

Migration is **in progress**. The MCP backend is feature-complete through CRUD + analytics, but the Streamlit chat path is not yet migrated. See `docs/build_plan.md` and `CLAUDE.md` for detailed status and next steps.

## Notes & tips

- **Do not remove OpenAI code** until MCP cutover is complete.
- **Feature flag**: switch `USE_MCP_BACKEND` to `true` to route SMS through MCP.
- **Twilio local testing**: use ngrok to expose the backend to Twilio webhooks.

## Related docs

- `CLAUDE.md` — comprehensive architecture and design notes
- `BACKEND_API_CONTRACT.md` — MCP chat frontend contract
- `docs/build_plan.md` — migration roadmap and status
