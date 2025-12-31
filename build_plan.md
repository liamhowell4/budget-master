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

## Phase 4: MCP Migration (Conversational Expense Management)

### Overview
Migrate SMS expense processing from OpenAI API to MCP (Model Context Protocol) architecture using Claude API and custom MCP client. This enables full conversational expense management via SMS: creating, editing, deleting, and querying expenses through natural language.

**Migration Strategy**: Dual-backend approach - keep existing OpenAI backend running while building and testing MCP implementation. Switch over only when MCP is fully functional.

### Architecture Comparison

**Current (OpenAI)**:
```
SMS → Twilio → FastAPI → OpenAI API → Firebase
```

**Target (MCP)**:
```
SMS → Twilio → FastAPI → MCP Client → Claude API → MCP Server (tools) → Firebase
```

**During Migration**:
```
SMS → Twilio → FastAPI → [OpenAI Backend OR MCP Backend] → Firebase
```

### New Capabilities Enabled by MCP

**Edit/Update**:
- "Actually that coffee was $6, not $5"
- "Change yesterday's lunch to GROCERIES category"
- "Update my rent payment to $1450"

**Query/Search**:
- "How much did I spend on food last week?"
- "Show me all my Uber expenses in December"
- "What was my biggest restaurant expense this month?"

**Delete**:
- "Delete that last coffee expense"
- "Remove the duplicate Chipotle charge"

**Budget Questions**:
- "How much of my food budget is left?"
- "Am I over budget in any categories?"

**Analytics**:
- "What's my average daily spending?"
- "Compare this month's food spending to last month"

---

### 4.1 Phase 1: Basic MCP Infrastructure ✅
**Goal**: Replace expense parsing with MCP, maintain same functionality as OpenAI

**Files Created**:
- `backend/mcp/__init__.py`
- `backend/mcp/expense_server.py` - MCP server with expense tools
- `backend/mcp/client.py` - Wrapper around custom MCP client
- `backend/system_prompts.py` - Centralized system prompt storage

**Files Modified**:
- `backend/api.py` - Add `/twilio/webhook-mcp` endpoint, MCP startup logic, feature flag
- `mcp-client/client.py` - Updated to use standard Anthropic SDK (removed AnthropicFoundry)
- `requirements.txt` - Added `anthropic>=0.18.0` and `mcp>=0.9.0`

**Tasks**:
- [x] Add `ANTHROPIC_API_KEY` to `.env` [ALREADY EXISTS IN .ENV]
- [x] Install Anthropic SDK (`anthropic>=0.18.0`)
- [x] Create `backend/mcp/` directory structure
- [x] Create `backend/system_prompts.py` with expense parsing system prompt
- [x] Implement MCP server with basic tools:
  - [x] `save_expense(name, amount, date, category)` - Wraps `firebase_client.save_expense()`
  - [x] `get_budget_status(category, amount, year, month)` - Wraps `budget_manager.get_budget_warning()`
  - [x] `get_categories()` - Returns valid ExpenseType categories
- [x] Create MCP client wrapper (`backend/mcp/client.py`)
  - [x] Integrate custom MCP client (stdio transport)
  - [x] Implement `process_expense_message(text, image_base64?)` method
  - [x] Update mcp-client to use standard Anthropic SDK
- [x] Add new FastAPI endpoint: `POST /twilio/webhook-mcp`
  - [x] Process SMS via MCP client instead of OpenAI
  - [x] Maintain same response format
  - [x] Add feature flag: `USE_MCP_BACKEND = False` (default OpenAI)
  - [x] Add MCP client startup logic in FastAPI
- [x] Testing:
  - [x] "Starbucks $5" saves correctly (saved as COFFEE, $5.00)
  - [x] Budget warnings match OpenAI output ("ℹ️ 88% of COFFEE budget used ($6.00 left)")
  - [x] Receipt images (MMS) processed via Claude Vision (Jamba Juice receipt: $12.89, FOOD_OUT)
  - [x] Can switch between backends with feature flag (verified both work independently)

**Success Criteria**:
- ✅ MCP backend achieves feature parity with OpenAI for expense creation
- ✅ Both backends can run in parallel
- ✅ Response format identical between OpenAI and MCP
- ✅ Claude Vision successfully extracts merchant, amount, and date from receipt images
- ✅ Tool orchestration works correctly (save_expense → get_budget_status)

**Status**: 🟢 Complete (2025-12-30)

---

### 4.2 Phase 2: Conversation State Management ⏳
**Goal**: Enable short-term context for "actually that was..." style edits

**Architecture Decision**: Use **in-memory cache** (Python dict) instead of Firebase for conversation state
- **Why**: Single user, short-term context (1-2 messages), queries hit database not conversation history
- **Trade-off**: Lost on API restart, but acceptable for local dev and rare restarts
- **Future**: Migrate to Redis when scaling to multiple users

**Files Created**:
- `backend/mcp/conversation_cache.py` - In-memory conversation state cache

**Files Modified**:
- None (FastAPI endpoint will use the cache)

**Tasks**:
- [ ] Implement `ConversationCache` class in `backend/mcp/conversation_cache.py`:
  - [ ] `update_last_expense(phone_number, expense_id)` - Track most recent expense
  - [ ] `get_last_expense_id(phone_number)` - Get last expense ID for "actually" edits
  - [ ] `get_recent_expenses(phone_number, limit=5)` - Get last 5 expense IDs
  - [ ] `cleanup_old(ttl_hours=24)` - Remove stale entries (manual cleanup)
  - [ ] Store in Python dict: `{phone_number: {last_expense_id, recent_expenses[], last_updated}}`
- [ ] Create global cache instance for FastAPI to use
- [ ] Update system prompt to reference recent expenses for "that", "last one"
- [ ] Add cache update after saving expense in MCP flow
- [ ] Test context-aware edits:
  - [ ] "Starbucks $5" → "Actually make that $6"
  - [ ] "Coffee $5" → "Delete that last expense"
  - [ ] Verify cache tracks last 5 expenses correctly

**Success Criteria**:
- ✅ "Actually that was $6" updates most recent expense
- ✅ "Delete that" removes correct expense
- ✅ Cache is fast (<1ms lookup)
- ✅ No Firestore overhead for conversation state

**Status**: 🟡 Not Started

---

### 4.3 Phase 3: CRUD Tools ⏳
**Goal**: Enable full expense management via SMS

**Files Modified**:
- `backend/mcp/expense_server.py` - Add CRUD tools

**Tasks**:
- [ ] Add MCP tools to expense server:
  - [ ] `update_expense(expense_id, name?, amount?, date?, category?)` - Edit expense
  - [ ] `delete_expense(expense_id)` - Remove expense
  - [ ] `get_expense_by_id(expense_id)` - Fetch single expense
  - [ ] `get_recent_expenses(limit?, category?)` - Last N expenses
  - [ ] `search_expenses(text_query)` - Fuzzy search by expense name
- [ ] Implement confirmation flows for destructive actions:
  - [ ] System prompt instructs Claude to confirm deletes
  - [ ] Show what will be deleted before confirming
  - [ ] If ambiguous, show options to user
- [ ] Test CRUD operations:
  - [ ] "Update my rent to $1450"
  - [ ] "Delete that last Starbucks expense"
  - [ ] "Show me my recent coffee purchases" → "Delete the first one"
  - [ ] Verify confirmation required for deletes

**Success Criteria**:
- ✅ Can edit any expense field via natural language
- ✅ Delete requires confirmation (prevents accidents)
- ✅ Search returns correct expenses

**Status**: 🟡 Not Started

---

### 4.4 Phase 4: Query & Analytics Tools ⏳
**Goal**: Answer questions about spending patterns

**Files Modified**:
- `backend/mcp/expense_server.py` - Add query/analytics tools

**Tasks**:
- [ ] Add analytics MCP tools:
  - [ ] `query_expenses(category?, start_date?, end_date?, limit?)` - Flexible filtering
  - [ ] `get_spending_by_category(start_date?, end_date?)` - Category breakdown
  - [ ] `get_spending_summary(start_date?, end_date?)` - Total + average
  - [ ] `get_budget_remaining(category?)` - Budget left in category
  - [ ] `compare_periods(period1_start, period1_end, period2_start, period2_end)` - Month-over-month
- [ ] Enhance system prompt for relative date parsing:
  - [ ] "last week" → Calculate start/end dates
  - [ ] "this month" → First day to today
  - [ ] "December" → Dec 1 to Dec 31
- [ ] Format responses for SMS (concise, <160 chars when possible)
- [ ] Test analytics queries:
  - [ ] "How much did I spend on food last week?"
  - [ ] "Am I over budget in any category?"
  - [ ] "Compare this month's food spending to last month"

**Success Criteria**:
- ✅ Answers budget questions accurately
- ✅ Handles relative date queries
- ✅ Formats responses concisely for SMS

**Status**: 🟡 Not Started

---

### 4.5 Phase 5: Streamlit Chat Migration ⏳
**Goal**: Migrate Streamlit chat interface to use same MCP backend

**Files Modified**:
- `frontend/app.py` - Update chat to call MCP backend

**Tasks**:
- [ ] Update Streamlit chat interface:
  - [ ] Call `/twilio/webhook-mcp` instead of OpenAI parsing
  - [ ] Maintain conversation state in Streamlit session
  - [ ] Display MCP responses in chat
- [ ] Test Streamlit chat:
  - [ ] Can edit/delete/query expenses like SMS
  - [ ] Voice transcription → MCP processing works
  - [ ] Image upload → MCP processing works
  - [ ] No regressions in existing features

**Success Criteria**:
- ✅ Chat interface has same capabilities as SMS
- ✅ Unified backend across SMS and Streamlit

**Status**: 🟡 Not Started

---

### 4.6 Phase 6: Cutover & OpenAI Deprecation ⏳
**Goal**: Switch to MCP as primary backend, archive OpenAI code

**Tasks**:
- [ ] Run both backends in parallel for 1 week
  - [ ] Monitor error rates
  - [ ] Compare response times (target: <3 seconds)
  - [ ] Compare costs (Claude API vs OpenAI)
- [ ] Production cutover:
  - [ ] Set `USE_MCP_BACKEND = True` in production
  - [ ] Update Twilio webhook to use `/twilio/webhook-mcp` by default
- [ ] Archive OpenAI code (DO NOT DELETE):
  - [ ] Move `expense_parser.py` to `legacy/expense_parser.py`
  - [ ] Move `endpoints.py` to `legacy/endpoints.py`
  - [ ] Keep files for rollback if needed
- [ ] Update documentation:
  - [ ] Update `CLAUDE.md` with MCP architecture
  - [ ] Update `README.md` with new conversational capabilities
  - [ ] Document conversation management

**Success Criteria**:
- ✅ All SMS/Streamlit traffic uses MCP
- ✅ OpenAI code safely archived (not deleted)
- ✅ Error rate < 1%
- ✅ Response time < 3 seconds

**Status**: 🟡 Not Started

---

### Rollback Plan
If MCP has critical issues:
1. Set `USE_MCP_BACKEND = False`
2. Route Twilio webhook back to `/twilio/webhook` (OpenAI)
3. OpenAI code remains in `legacy/` until MCP is stable

**Rollback Triggers**:
- Response time > 5 seconds
- Error rate > 5%
- Incorrect parsing > 10% of requests

---

### Data Schemas

**In-Memory Conversation Cache** (`backend/mcp/conversation_cache.py`):
```python
# Structure stored in Python dict
{
    "+1234567890": {  # phone_number key
        "last_expense_id": "abc123",
        "recent_expenses": ["abc123", "def456", "ghi789"],  # Last 5
        "last_updated": datetime(2025, 12, 30, 10, 30, 0)
    }
}
```

**No Pydantic Models Required** - Simple dict structure, no database serialization needed

---

### Environment Variables

Add to `.env`:
```bash
# Anthropic/Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Feature Flags
USE_MCP_BACKEND=false  # Set to true after testing
```

**Note**: Conversation cache settings (TTL, size limits) are hardcoded in `conversation_cache.py` since it's in-memory and single-user

---

### Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 4.1: Basic MCP | 1-2 weeks | MCP parity with OpenAI |
| 4.2: Conversation State | 2-3 days | Context-aware edits (in-memory cache) |
| 4.3: CRUD Tools | 1 week | Full management via SMS |
| 4.4: Analytics Tools | 1 week | Query capabilities |
| 4.5: Streamlit Migration | 1 week | Unified backend |
| 4.6: Cutover | 1 week | Production migration |

**Total**: 4-6 weeks (part-time development)

---

**Overall Phase 4 Status**: 🔵 In Progress
- ✅ **Phase 4.1 (Basic MCP Infrastructure)** - Complete (2025-12-30)
- 🟡 **Phase 4.2 (Conversation State)** - Not Started
- 🟡 **Phase 4.3 (CRUD Tools)** - Not Started
- 🟡 **Phase 4.4 (Analytics Tools)** - Not Started
- 🟡 **Phase 4.5 (Streamlit Migration)** - Not Started
- 🟡 **Phase 4.6 (Cutover)** - Not Started

---

## Phase 5: Audio/Voice Features

### 5.1 Add Whisper Transcription ⏳
**File**: `whisper_client.py`
- [ ] Create `WhisperClient` class
- [ ] Implement `transcribe_audio(audio_bytes)` method
- [ ] Handle various audio formats
- [ ] Test transcription accuracy

### 5.2 Add Voice Recording to Streamlit ⏳
**File**: `app.py` (continued)
- [ ] Add audio recording component
- [ ] Upload audio to Firebase Storage
- [ ] Call Whisper transcription
- [ ] Process transcription as text input
- [ ] Display transcription to user
- [ ] Test end-to-end voice flow

### 5.3 Firebase Storage Integration ⏳
**File**: `firebase_client.py` (update)
- [ ] Add `upload_audio(audio_bytes, filename)` method
- [ ] Add `get_audio_url(filename)` method
- [ ] Configure storage bucket permissions
- [ ] Test audio upload/retrieval

**Status**: 🟡 Not Started

---

## Phase 6: Cleanup & Testing

### 6.1 Remove Obsolete Files ⏳
- [ ] Delete `function_app.py` (Azure Functions)
- [ ] Delete `bot_handler.py` (Teams Bot Framework)
- [ ] Delete `adaptive_cards.py` (Teams cards)
- [ ] Update `.gitignore` if needed

### 6.2 Update Dependencies ⏳
**File**: `requirements.txt`
- [ ] Remove Azure Functions dependencies
- [ ] Remove `httpx` if not used
- [ ] Add `firebase-admin`
- [ ] Add `twilio`
- [ ] Add `streamlit` audio components
- [ ] Pin versions for stability

### 6.3 Integration Testing ⏳
- [ ] Test SMS text-only expense
- [ ] Test MMS with receipt image
- [ ] Test SMS with natural language date
- [ ] Test budget warnings at all thresholds
- [ ] Test Streamlit manual entry
- [ ] Test voice recording flow
- [ ] Test with missing/invalid data

### 6.4 Documentation ⏳
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

## Current Phase: Phase 4 - MCP Migration 🔵 IN PROGRESS

**Current Sub-Phase**: Phase 4.1 🟢 COMPLETE (2025-12-30)

### Phase 4.1 - Basic MCP Infrastructure (COMPLETE)

**Files Created**:
- ✅ `backend/mcp/__init__.py` - MCP module initialization
- ✅ `backend/mcp/expense_server.py` - MCP server with stdio transport and 3 tools
- ✅ `backend/mcp/client.py` - FastAPI wrapper for MCP client with expense message processing
- ✅ `backend/system_prompts.py` - Centralized system prompt storage

**Files Modified**:
- ✅ `backend/api.py` - Added `/twilio/webhook-mcp` endpoint, MCP startup logic, feature flag
- ✅ `mcp-client/client.py` - Updated to use standard Anthropic SDK
- ✅ `requirements.txt` - Added anthropic>=0.18.0 and mcp>=0.9.0

**Test Results**:
- ✅ Text parsing: "Starbucks $5" → COFFEE, $5.00
- ✅ Budget warnings: "ℹ️ 88% of COFFEE budget used ($6.00 left)"
- ✅ Image processing: Jamba Juice receipt → $12.89, FOOD_OUT, extracted merchant/date
- ✅ Feature flag: Both OpenAI and MCP backends work independently
- ✅ Tool orchestration: save_expense → get_budget_status working correctly

**Next Steps**: Phase 4.2 (Conversation State Management) - Add in-memory cache for multi-turn conversations

---

### Previous Completed Phases

**Phase 3 - Input/Output Layer**: 🟢 COMPLETE (2025-12-26)
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

Last Updated: 2025-12-30
