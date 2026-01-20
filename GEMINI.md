# Finance Bot (Budget Master)

## Project Overview

**Budget Master** is a personal expense tracking and budgeting application designed to make financial tracking effortless. It supports multi-modal inputs (Text, Image, Voice) and leverages advanced AI (OpenAI and Anthropic) to parse expenses and manage budgets in real-time.

**Key Features:**
*   **Multi-Modal Input:** Add expenses via SMS/MMS (Twilio) or a Web UI (Streamlit).
*   **AI-Powered Parsing:** Uses GPT-4 Vision for receipts, Whisper for voice, and LLMs for natural language text parsing.
*   **Real-time Budgeting:** Tracks spending against monthly caps per category and overall, sending alerts at specific thresholds (50%, 90%, 95%, 100%+).
*   **Recurring Expenses:** automated detection and management of recurring bills.
*   **Dual Backend (Migration):** Currently running a hybrid architecture, migrating from direct OpenAI calls to the Model Context Protocol (MCP) with Claude.

## Architecture

The project follows a modular architecture separating the frontend, backend, and data layers.

### Core Components

*   **Backend (`backend/`):** A FastAPI application that serves as the core logic hub.
    *   `api.py`: Main entry point, defines endpoints for Twilio webhooks and Streamlit.
    *   `expense_parser.py`: Logic for extracting expense details from inputs (OpenAI).
    *   `budget_manager.py`: Handles budget calculations and threshold warnings.
    *   `firebase_client.py`: Interface for Firestore and Firebase Storage.
    *   `mcp/`: New module containing the MCP server and client for the migration.
*   **Frontend (`frontend/`):** A Streamlit application (`app.py`) providing a chat interface, dashboard, and manual entry tools.
*   **Database:** Google Firebase Firestore (NoSQL) for storing expenses, budgets, and categories.
*   **Storage:** Google Firebase Storage for audio recordings.
*   **External Services:**
    *   **Twilio:** Handles SMS/MMS communication.
    *   **OpenAI:** Provides GPT-4 Vision, GPT-4, and Whisper models.
    *   **Anthropic:** Provides Claude models for the new MCP-based workflow.

### Data Flow (Simplified)

1.  **Input:** User sends an SMS/MMS or interacts with the Streamlit UI.
2.  **Processing:**
    *   **SMS:** Twilio hits the FastAPI webhook (`/twilio/webhook` or `/twilio/webhook-mcp`).
    *   **UI:** Streamlit sends data to internal helper functions or API endpoints.
3.  **Parsing:** AI models extract `amount`, `category`, `date`, and `expense_name`.
4.  **Logic:** System checks budget caps and generates warnings if thresholds are crossed.
5.  **Storage:** Validated data is saved to Firestore.
6.  **Feedback:** User receives a confirmation message (via SMS or UI) with current budget status.

## Setup & Development

### Prerequisites

*   Python 3.11+
*   Firebase Service Account credentials
*   Twilio Account (SID, Token, Secret)
*   OpenAI API Key
*   Anthropic API Key

### Installation

1.  **Clone & Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables:**
    Create a `.env` file with the following keys:
    *   `OPENAI_API_KEY`
    *   `FIREBASE_KEY` (path to JSON or raw JSON content)
    *   `TWILIO_ACCOUNT_SID`, `TWILIO_ACCOUNT_TOKEN`, `TWILIO_SECRET_SID`, `TWILIO_SECRET_KEY`
    *   `ANTHROPIC_API_KEY`
    *   `USE_MCP_BACKEND` (Set to `false` for stable, `true` for experimental MCP)

### Running the Application

*   **Start Backend:**
    ```bash
    uvicorn backend.api:app --reload --port 8000
    ```

*   **Start Frontend:**
    ```bash
    streamlit run frontend/app.py
    ```

### Testing

*   **Run Budget Manager Tests:**
    ```bash
    python tests/test_budget_manager.py
    ```
*   **Seed Firestore (Caution):**
    ```bash
    python scripts/seed_firestore.py
    ```

## MCP Migration (In Progress)

The project is moving towards a **Model Context Protocol (MCP)** architecture to enable conversational interactions (e.g., "edit that last expense to $5").

*   **Current State:** Dual backend.
    *   `USE_MCP_BACKEND=false`: Uses legacy `expense_parser.py` (OpenAI).
    *   `USE_MCP_BACKEND=true`: Uses `backend/mcp/` components (Claude).
*   **Goal:** Replace the rigid parser with an intelligent agent that can call tools (`save_expense`, `update_expense`, `get_budget`) based on user intent.

## Conventions

*   **Imports:** Use relative imports within the `backend` module (e.g., `from .firebase_client import ...`).
*   **Dates:** Store and manipulate dates using the `Date` schema (day, month, year) defined in `output_schemas.py`.
*   **Categories:** strictly adhere to the `ExpenseType` enum.
*   **Formatting:** Follow standard Python PEP 8 guidelines.
