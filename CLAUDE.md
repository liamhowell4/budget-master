# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A personal expense tracking and budgeting app that accepts expenses via multiple input methods:
- **SMS/MMS via Twilio** - Send expense info as text or receipt images from mobile
- **Streamlit Web UI** - Record voice memos or upload images from desktop/web

All inputs are processed using OpenAI APIs (GPT-4 Vision for images, Whisper for voice transcription, GPT for text parsing) and stored in Firebase Firestore. The app focuses on budget management with monthly caps and real-time budget warnings.

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

## Architecture

### Core Components

**FastAPI Backend** (`api.py` - to be expanded)
- `/twilio/webhook` - Receives SMS/MMS from Twilio, processes expense, saves to Firestore, responds via SMS
- `/streamlit/process` - Receives voice/image from Streamlit UI, processes and saves
- `/health` - Health check endpoint

**Streamlit Frontend** (`app.py` - to be updated)
- Voice recording interface with audio upload to Firebase Storage
- Optional image upload for receipts
- Displays expense history and budget status
- Runs on localhost (eventually web-deployed)

**Expense Parser** (`expense_parser.py`)
- Handles three input types: text, images, voice transcriptions
- Uses OpenAI GPT-4 Vision for receipt images
- Uses OpenAI GPT for text/transcription parsing
- Extracts: expense_name, amount, date, category
- **Note**: Remove `participants` and `project_name` fields - not needed for personal expenses

**Data Schemas** (`output_schemas.py`)
- `Expense`: Main expense model with fields:
  - `expense_name` (str) - Auto-generated descriptive name
  - `amount` (float)
  - `date` (Date) - Supports natural language like "yesterday", "last Tuesday"
  - `category` (ExpenseType enum)
  - **REMOVE**: `participants`, `project_name` (business expense fields, not needed)
- `ExpenseType` enum: FOOD_OUT, RENT, UTILITIES, MEDICAL, GAS, GROCERIES, RIDE_SHARE, COFFEE, HOTEL, TECH, TRAVEL, OTHER
- `Date`: day, month, year

**Firebase Integration** (new module needed)
- Firestore collections:
  - `expenses/` - Flat structure with timestamp filters
  - `budget_caps/` - Per-category monthly caps + total monthly cap
  - `categories/` - Enum key and value for each category
- Firebase Storage: Audio recordings from Streamlit UI

**Twilio Integration** (new module needed)
- Webhook handler for incoming SMS/MMS
- Image download from Twilio
- SMS response sender with budget warnings

**OpenAI Clients** (`endpoints.py` - to be updated)
- Currently uses Azure OpenAI endpoints - **UPDATE** to use standard OpenAI API
- Remove Anthropic clients (not needed)
- Add Whisper transcription client

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
uvicorn api:app --reload --port 8000

# Start Streamlit UI (separate terminal)
streamlit run app.py
```

### Testing
Currently no test suite. Manual testing via:
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
- **ALWAYS** include warning if over budget (>100%)
- Apply to both category-level and total budget
- Include in SMS responses and Streamlit UI

Example responses:
- `✅ Saved $50 Groceries (GROCERIES) ℹ️ 50% of monthly budget used`
- `✅ Saved $15 Coffee (COFFEE) ⚠️ 95% of COFFEE budget used`
- `✅ Saved $200 Rent (RENT) 🚨 OVER BUDGET! 105% of monthly total budget used`

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

### Firebase Storage
- Audio recordings: `audio_recordings/{timestamp}_{user_id}.webm`

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

## Current State vs. Target State

### Files to Remove/Replace:
- `function_app.py` - Azure Functions entry point (not needed)
- `bot_handler.py` - Teams Bot Framework handler (not needed)
- `adaptive_cards.py` - Teams Adaptive Cards (not needed)
- Most of current `endpoints.py` - Azure OpenAI + Anthropic (replace with standard OpenAI)

### Files to Keep/Modify:
- `output_schemas.py` - Keep, but **remove** `participants` and `project_name` fields
- `expense_parser.py` - Keep core logic, update to handle text/voice/image inputs
- `app.py` - Update for voice recording + expense history UI
- `api.py` - Expand with Twilio and Streamlit endpoints

### Files to Create:
- `firebase_client.py` - Firestore operations, Storage uploads
- `twilio_handler.py` - SMS/MMS webhook handling, response sending
- `budget_manager.py` - Budget calculation, warning generation
- `whisper_client.py` - Audio transcription with OpenAI Whisper
- `voice_processor.py` - Handle Streamlit audio upload + transcription

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
