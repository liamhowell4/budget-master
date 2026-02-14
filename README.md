# BudgetMaster

A personal expense tracking and budgeting app with conversational AI. Talk to it in plain English to log expenses, ask spending questions, and manage budgets — via web, voice, or receipt photos.

## Features

- **Natural language expense entry** — "Coffee $5 yesterday", "Got a $20 refund from Amazon"
- **Receipt scanning** — Upload a photo and Claude Vision extracts merchant, amount, date, and category
- **Voice memos** — Record audio, Whisper transcribes it, expense is logged
- **Conversational editing** — "Actually that was $6", "Delete that last one", "Change it to GROCERIES"
- **Spending queries** — "How much did I spend on food last week?", "Compare this month to last month"
- **Budget tracking** — Warnings at 50%, 90%, 95%, and 100%+ of category and overall budgets
- **Recurring expenses** — Templates for rent, subscriptions, etc. with automatic pending reminders

## Architecture

```
User (Web / iOS / API)
        ↓
   FastAPI Backend
        ↓
   MCP Client → Claude API → MCP Server (17 tools) → Firebase Firestore
```

The backend uses [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to give Claude access to expense management tools. Claude decides which tools to call based on the user's message — no rigid intent classification or regex parsing.

### Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Anthropic SDK, MCP |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4 |
| iOS | Swift, SwiftUI (networking layer complete, UI in progress) |
| Database | Firebase Firestore |
| Storage | Firebase Storage (audio files) |
| AI | Claude (conversation + vision), Whisper (transcription) |
| Auth | Firebase Authentication |
| Hosting | Google Cloud Run |

## Repository layout

```
backend/                 FastAPI backend, Firebase client, MCP tools
frontend/                React frontend (Vite + TypeScript + Tailwind)
ios/                     iOS app (Swift networking layer + Xcode project)
tests/                   Budget manager tests
scripts/                 Utility scripts (Firestore seeding)
docs/                    Implementation plans and notes
legacy/                  Archived OpenAI code (not used)
CLAUDE.md                Architecture reference and dev guidance
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

- **Chat page** — Conversational expense entry with text, image upload, and voice recording
- **Dashboard page** — Budget summaries, category progress bars, and spending analytics
- **Expenses page** — Filterable expense history, pending confirmations, and recurring templates
- **Login page** — Firebase authentication

## iOS app

The iOS app (`ios/`) targets the same backend API. Current state:

- **Networking layer** — Complete. Actor-based `APIClient`, typed `APIError`, SSE streaming via `SSEClient`, multipart uploads
- **Models** — All Codable structs matching backend responses (expenses, budgets, categories, chat events, etc.)
- **Services** — Stateless endpoint wrappers for all 25+ API endpoints
- **SwiftUI views** — Not yet started

See `docs/ios-networking-layer.md` for architecture details and Xcode setup instructions.

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

## Current status

| Component | Status |
|-----------|--------|
| **Backend (FastAPI + MCP)** | Complete — 17 MCP tools, conversation context, budget tracking, recurring expenses |
| **React frontend** | Complete — chat, dashboard, expense management, auth |
| **iOS app** | In progress — networking layer done (models, services, SSE streaming), SwiftUI views not yet built |
| **Code cleanup** | In progress — logging migration done, error handling improved, frontend refactoring planned |
| **Deployment** | Live on Google Cloud Run, recurring checks via Cloud Scheduler |

## Related docs

- `CLAUDE.md` — architecture reference and development guidance
- `docs/build_plan.md` — full development history across all phases
- `docs/ios-networking-layer.md` — iOS networking architecture and setup guide
- `docs/code-audit-cleanup.md` — ongoing cleanup plan and progress
