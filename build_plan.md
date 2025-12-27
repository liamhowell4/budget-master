# Build Plan - Personal Expense Tracker

This document tracks the implementation progress for converting the Teams expense bot into a personal expense tracker with Twilio SMS/MMS and Streamlit UI.

## Phase 1: Foundation (Data Layer)

### 1.1 Update Data Schemas ✅
**File**: `output_schemas.py`
- [x] Remove `participants` field from `Expense` model
- [x] Remove `project_name` field from `Expense` model
- [x] Removed `Name` class (no longer needed)
- [x] Verify `ExpenseType` enum matches personal expense categories

### 1.2 Create Firebase Client ✅
**File**: `firebase_client.py`
- [x] Initialize Firebase Admin SDK
- [x] Create `FirebaseClient` class
- [x] Implement `save_expense(expense: Expense)` method
- [x] Implement `get_expenses(start_date, end_date)` method
- [x] Implement `get_monthly_expenses(year, month)` method
- [x] Implement `calculate_monthly_total(year, month)` method
- [x] Implement `get_budget_cap(category)` method
- [x] Implement `set_budget_cap(category, amount)` method
- [x] Implement `get_all_budget_caps()` method
- [x] Implement `get_category_data()` method
- [x] Implement `seed_categories()` method
- [x] Implement `upload_audio()` and `get_audio_url()` for Firebase Storage

### 1.3 Initialize Firestore Collections ✅
**File**: `seed_firestore.py` (new script)
- [x] Create script to seed `categories` collection from `ExpenseType` enum
- [x] Create default `budget_caps` collection entries
- [x] Add sample expenses for testing (optional, commented out)
- [x] Document how to run seed script

**Status**: 🟢 Complete

---

## Phase 2: Processing Layer

### 2.1 Update OpenAI Endpoints ✅
**File**: `endpoints.py`
- [x] Remove Azure OpenAI configuration
- [x] Remove Anthropic/AnthropicFoundry clients
- [x] Add standard OpenAI client initialization
- [x] Add OpenAI async client
- [x] Test OpenAI connection

### 2.2 Update Expense Parser ✅
**File**: `expense_parser.py`
- [x] Update to use standard OpenAI API (not Azure)
- [x] Remove references to participants and project_name
- [x] Update AI prompt for personal expenses
- [x] Fix category mapping to match personal categories (FOOD_OUT, RENT, etc.)
- [x] Add support for natural language dates ("yesterday", "last Tuesday")
- [x] Add text-only parsing (no image required)
- [x] Test with various input types

### 2.3 Create Budget Manager ✅
**File**: `budget_manager.py`
- [x] Create `BudgetManager` class
- [x] Implement `calculate_monthly_spending(category, year, month)` method
- [x] Implement `calculate_total_monthly_spending(year, month)` method
- [x] Implement `get_budget_warning(category, amount, year, month)` method
- [x] Implement warning threshold logic (50%, 90%, 95%, 100%+)
- [x] Format warning messages with appropriate emojis and dollars remaining
- [x] Test budget calculations and warnings

**Status**: 🟢 Complete

---

## Phase 3: Input/Output Layer

### 3.1 Create Twilio Handler ✅
**File**: `twilio_handler.py`
- [x] Create `TwilioHandler` class
- [x] Implement `download_mms_media(media_url)` method (supports up to 3 images)
- [x] Implement `parse_incoming_message(form_data)` method
- [x] Implement `send_sms(to, message)` method
- [x] Add request signature validation for security
- [x] Implement phone number verification (USER_PHONE_NUMBER)
- [x] Add timezone support (Central US Time)
- [x] Implement "status" and "total" command handlers
- [x] Format SMS response with expense details and budget warnings
- [x] Add retry logic for Firebase failures
- [x] Create `.env.example` with all required variables
- [x] Update `requirements.txt` with pytz and requests

**Status**: 🟢 Complete

### 3.2 Update FastAPI Backend ✅
**File**: `api.py`
- [x] Remove old `/parse-receipt` endpoint
- [x] Add CORS middleware for Streamlit cross-origin requests
- [x] Add `/twilio/webhook` POST endpoint with signature validation
- [x] Implement full flow: receive → parse → save → budget check → respond
- [x] Add `/streamlit/process` POST endpoint (text/image/audio support)
- [x] Add `/expenses` GET endpoint with year/month/category filtering
- [x] Add `/budget` GET endpoint with all category data
- [x] Add lazy initialization for TwilioHandler
- [x] Test endpoints (health, budget)

**Status**: 🟢 Complete

### 3.3 Update Streamlit UI ✅
**File**: `app.py`
- [x] Remove old receipt parsing UI
- [x] Add tab-based navigation (Dashboard, Add Expense, History)
- [x] Add budget status dashboard with summary metrics
- [x] Add color-coded progress bars for each category
- [x] Add manual expense entry form (text + optional image)
- [x] Add month/year filters for Dashboard and History
- [x] Add category filter for expense history
- [x] Add expense history table with sortable columns
- [x] Add CSV download functionality
- [x] Add collapsible filter expander
- [x] Style with Claude-themed colors (orange #CC785C)
- [x] Add dark mode support with CSS
- [x] Add budget warning color coding (green/blue/orange/red)
- [x] Add auto-refresh after expense submission
- [x] Test UI functionality with API server

**Status**: 🟢 Complete

---

## Phase 4: Advanced Features

### 4.1 Add Whisper Transcription ⏳
**File**: `whisper_client.py`
- [ ] Create `WhisperClient` class
- [ ] Implement `transcribe_audio(audio_bytes)` method
- [ ] Handle various audio formats
- [ ] Test transcription accuracy

### 4.2 Add Voice Recording to Streamlit ⏳
**File**: `app.py` (continued)
- [ ] Add audio recording component
- [ ] Upload audio to Firebase Storage
- [ ] Call Whisper transcription
- [ ] Process transcription as text input
- [ ] Display transcription to user
- [ ] Test end-to-end voice flow

### 4.3 Firebase Storage Integration ⏳
**File**: `firebase_client.py` (update)
- [ ] Add `upload_audio(audio_bytes, filename)` method
- [ ] Add `get_audio_url(filename)` method
- [ ] Configure storage bucket permissions
- [ ] Test audio upload/retrieval

**Status**: 🟡 Not Started

---

## Phase 5: Cleanup & Testing

### 5.1 Remove Obsolete Files ⏳
- [ ] Delete `function_app.py` (Azure Functions)
- [ ] Delete `bot_handler.py` (Teams Bot Framework)
- [ ] Delete `adaptive_cards.py` (Teams cards)
- [ ] Update `.gitignore` if needed

### 5.2 Update Dependencies ⏳
**File**: `requirements.txt`
- [ ] Remove Azure Functions dependencies
- [ ] Remove `httpx` if not used
- [ ] Add `firebase-admin`
- [ ] Add `twilio`
- [ ] Add `streamlit` audio components
- [ ] Pin versions for stability

### 5.3 Integration Testing ⏳
- [ ] Test SMS text-only expense
- [ ] Test MMS with receipt image
- [ ] Test SMS with natural language date
- [ ] Test budget warnings at all thresholds
- [ ] Test Streamlit manual entry
- [ ] Test voice recording flow
- [ ] Test with missing/invalid data

### 5.4 Documentation ⏳
- [ ] Update README.md with new project description
- [ ] Add setup instructions
- [ ] Add example usage
- [ ] Document Twilio webhook setup with ngrok
- [ ] Document Firebase project setup

**Status**: 🟡 Not Started

---

## Progress Legend
- 🟢 **Complete**: All tasks done and tested
- 🟡 **Not Started**: No work begun
- 🔵 **In Progress**: Currently working on this phase
- ⏳ **Pending**: Individual task status (checkbox)

---

## Current Phase: Phase 3 - Input/Output Layer 🟢 COMPLETE

**Completed**: 2025-12-26

**Files Created/Modified**:
- ✅ `twilio_handler.py` - Complete SMS/MMS handler with signature validation, commands, and multi-image support
- ✅ `api.py` - FastAPI backend with 5 endpoints, CORS, and lazy Twilio initialization
- ✅ `app.py` - Full Streamlit UI with Claude theming, tabs, dashboard, expense entry, and history
- ✅ `.env.example` - Environment variable template
- ✅ `requirements.txt` - Updated dependencies (pytz, requests)

**Phase 2 - Processing Layer**: 🟢 COMPLETE
- ✅ `endpoints.py` - Migrated to standard OpenAI API (removed Azure/Anthropic)
- ✅ `expense_parser.py` - Updated for personal expenses with natural language date support
- ✅ `budget_manager.py` - Budget tracking with multi-threshold warnings and dollar amounts

**Phase 1 - Foundation (Data Layer)**: 🟢 COMPLETE
- ✅ `output_schemas.py` - Removed business expense fields (participants, project_name)
- ✅ `firebase_client.py` - Complete Firebase integration with Firestore and Storage
- ✅ `seed_firestore.py` - Initialization script for categories and budget_caps

**Next Steps**: Phase 4 (Audio/Voice) or Phase 5 (Cleanup & Testing)

Last Updated: 2025-12-26
