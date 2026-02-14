# Code Audit & Cleanup Plan

**Created:** 2026-02-14
**Status:** In Progress

---

## Phase 1: Security & Git Hygiene ✅

### 1.1 Secrets Removal
- [x] Run `git rm --cached .env` to stop tracking root `.env` (was already untracked)
- [x] Run `git rm --cached backend/.env` if tracked (was already untracked)
- [x] Add `frontend_streamlit/.env` to `.gitignore` (broadened `.env.*` pattern to cover all levels)
- [x] Verify no `.env` files with secrets remain tracked — untracked `frontend/.env.production`
- [x] **Post-merge reminder:** Rotate all exposed credentials (Anthropic, OpenAI, Firebase service account, Twilio)

### 1.2 Dead Files & Directories
- [x] Remove `frontend_streamlit/` directory (legacy Streamlit UI, superseded by React frontend)
- [x] Remove root-level `__pycache__/` directory
- [x] Remove `firebase-debug.log` from project root
- [x] Delete outdated `GEMINI.md` (references old dual-backend architecture that no longer exists)
- [x] Clean up `backups/` directory (old migration artifacts from Jan 2025)

### 1.3 .gitignore Fixes
- [x] Remove `.firebaserc` from `.gitignore` (now untracked, ready to commit)
- [x] Remove `firebase.json` from `.gitignore` (same)
- [x] Confirm `__pycache__/` ignore rule covers all levels (root + nested)
- [x] ~~Add `frontend_streamlit/` to `.gitignore` if directory is kept instead of deleted~~ (deleted entirely)

### 1.4 Git Status Cleanup
- [x] Resolve the 31 `AD` (added-then-deleted) iOS files with flattened names at repo root — removed all 30 flattened files from index + unstaged root `iOS_SETUP_GUIDE.md`

### 1.5 Additional Fixes (found during Phase 1)
- [x] Added `localhost:5173` (Vite default) to CORS allow list in `backend/api.py`
- [x] Deleted `budget-master-backend` Cloud Run service (failed deployment, never served traffic)
- [x] Disabled `budget-master` Cloud Run service (set ingress to internal-only)

---

## Phase 2: Backend Cleanup

### 2.1 Replace `print()` with `logging` ✅
All 67 `print()` calls replaced with the Python `logging` module.

- [x] Add `import logging` and configure logger at module level in each backend file
- [x] `backend/api.py` — Replace all `print()` calls (~40 instances) with appropriate log levels:
  - Startup messages → `logger.info()`
  - Error catches → `logger.error()`
  - Debug/trace output → `logger.debug()`
- [x] `backend/firebase_client.py` — Replace `print()` calls with `logger`
- [x] `backend/recurring_manager.py` — Replace `print()` calls with `logger`
- [x] `backend/mcp/expense_server.py` — Replace `print()` calls with `logger`
- [x] `backend/mcp/client.py` — Replace `print()` calls with `logger`
- [x] `backend/mcp/connection_manager.py` — Replace `print()` calls with `logger`
- [x] Any remaining files with `print()` statements

### 2.2 Error Handling ✅
- [x] `backend/whisper_client.py:23-27` — Wrap OpenAI Whisper API call in try-except, catch `APIError`, `TimeoutError`, return meaningful error
- [x] `backend/api.py:2017` — Wrap MCP `call_tool()` in try-except so tool failures don't crash the SSE stream
- [x] `backend/api.py:1978-1984` — Add error handling for Claude API call (catch `APIError`, `RateLimitError`)
- [x] `backend/firebase_client.py` — Add try-except to Firestore write operations (`add()`, `update()`, `set()`) in:
  - `save_expense()` (line ~131)
  - `update_expense()` (line ~328)
  - `save_budget_cap()` (line ~594)
  - `save_recurring_expense()`
- [ ] Standardize error pattern: prefer raising exceptions over returning `False` silently

### 2.3 Code Duplication ✅
- [x] `backend/firebase_client.py` — Consolidate `save_expense()` and `save_expense_with_category_str()` into a single method with an optional `category_str` parameter (lines 106-164, ~57 lines duplicated)
- [x] `backend/firebase_client.py` — Consolidate `save_recurring_expense()` and `save_recurring_expense_with_category_str()` into a single method (lines 1177-1250, ~73 lines duplicated)
- [x] `backend/api.py` — Extract repeated timestamp formatting logic into a `_format_timestamps()` helper function

### 2.4 Refactor `chat_stream()` (api.py:1862, 265 lines)
- [ ] Extract conversation state management into `_get_or_create_conversation()`
- [ ] Extract message context building into `_build_message_context()`
- [ ] Extract Claude API call + tool loop into `_run_claude_tool_loop()`
- [ ] Extract conversation saving into `_save_conversation_history()`
- [ ] Keep `chat_stream()` as the orchestrator that calls these helpers

### 2.5 Type Hint Fixes
- [ ] `backend/firebase_client.py:542` — Change lowercase `any` to `Any` (from typing)
- [ ] `backend/firebase_client.py:1571` — Change `tool_calls: list = None` to `Optional[List[Dict]]`
- [ ] `backend/firebase_client.py:1640` — Add specific type annotation for `date: Optional[Dict]`
- [ ] `backend/mcp/connection_manager.py:23` — Change `tools: List[Dict[str, str]] = None` to `Optional[List[...]]`
- [ ] `backend/api.py:1152` — Change `category_caps: dict` to `Dict[str, float]`
- [ ] Scan for any other missing or incorrect type hints

### 2.6 Constants Extraction
- [ ] Extract hardcoded model name `"claude-sonnet-4-5"` (appears twice in `api.py`) to a module-level constant `CLAUDE_MODEL`
- [ ] Extract `max_tokens=2000` to constant `CLAUDE_MAX_TOKENS`
- [ ] Extract `INACTIVITY_THRESHOLD_HOURS = 12` to module-level constant in `api.py`
- [ ] `backend/budget_manager.py` — Extract threshold values (50, 90, 95, 100) into a `BUDGET_THRESHOLDS` constant
- [ ] `backend/recurring_manager.py` — Extract magic numbers (14 days biweekly, etc.) into named constants

### 2.7 Security Hardening
- [ ] `backend/api.py:47-64` — Restrict CORS `allow_methods` from `["*"]` to `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`
- [ ] `backend/api.py:47-64` — Restrict CORS `allow_headers` from `["*"]` to specific required headers (`Content-Type`, `Authorization`, etc.)
- [ ] Review auth token handling in tool args (`api.py:2005`) — ensure tokens aren't logged

### 2.8 Input Validation
- [ ] `backend/api.py:449` — Validate `month` is 1-12 and `year` is reasonable before passing to `monthrange()`
- [ ] `backend/api.py:1112` — Move `total_monthly_budget < 0` check to top of handler
- [ ] Review other endpoints for missing validation on query parameters

---

## Phase 3: Frontend Cleanup

### 3.1 Deduplicate Shared Code
- [ ] Move `CATEGORY_LABELS` from `ChatPage.tsx` (lines 29-42) and `ExpensesPage.tsx` (lines 16-29) into `src/utils/constants.ts`
- [ ] Update all imports in `ChatPage.tsx`, `ExpensesPage.tsx`, and anywhere else referencing local `CATEGORY_LABELS`
- [ ] Move `sortExpenses()` from `ChatPage.tsx` (lines 53-74) and `ExpensesPage.tsx` (lines 48-63) into `src/utils/helpers.ts`
- [ ] Update all imports referencing local `sortExpenses`

### 3.2 Split Large Page Components

**ChatPage.tsx (703 lines):**
- [ ] Extract `<ChatSidebar>` component (conversation list, new chat button)
- [ ] Extract `<ChatMessageList>` component (message rendering, scroll behavior)
- [ ] Extract `<ChatInput>` component (text input, send button, example prompts)
- [ ] Extract `<CategoryExpensesModal>` if not already a shared component
- [ ] Keep `ChatPage.tsx` as layout orchestrator wiring these together

**ExpensesPage.tsx (672 lines):**
- [ ] Extract `<ExpenseItem>` component (individual expense row rendering)
- [ ] Extract `<PendingExpensesList>` component (pending tab content)
- [ ] Extract `<RecurringExpensesList>` component (recurring tab content)
- [ ] Extract `<ExpenseFilters>` component (date/category/sort filters)
- [ ] Keep `ExpensesPage.tsx` as layout orchestrator

### 3.3 Fix TypeScript Issues
- [ ] `src/hooks/useCategories.ts` — Replace `err: any` with proper error typing at lines 75, 92, 110, 134, 153
  - Use `catch (err: unknown)` + `err instanceof Error` pattern
- [ ] `src/hooks/usePending.ts` — Fix error handling pattern (lines 37, 49)
- [ ] `src/types/chat.ts:26` — Consider typing `result?: unknown` more specifically per tool type
- [ ] Remove unused imports:
  - `src/pages/ChatPage.tsx:1` — `useRef` if unused
  - `src/hooks/useChat.ts:6` — `ConversationListItem` if unused

### 3.4 DRY Up ExpenseEditModal
- [ ] `src/components/ui/ExpenseEditModal.tsx` — Extract the repeated date initialization logic (lines 45-52, 72-78, 89-95) into a single helper function like `getInitialDateState(expense)`
- [ ] Extract the repeated timestamp initialization into the same helper or a companion function

### 3.5 Performance: Memoization
- [ ] `src/pages/ChatPage.tsx` — Wrap handler functions (`handleDelete`, `handleEdit`, `handleSave`) in `useCallback`
- [ ] `src/pages/ChatPage.tsx` — Wrap category filtering logic (lines 316-323) in `useMemo`
- [ ] `src/pages/DashboardPage.tsx` — Wrap category filtering (lines 146-152) in `useMemo`
- [ ] Review other components for render-heavy inline computations

### 3.6 API Service Consistency
- [ ] `src/services/chatService.ts` — Replace raw `fetch()` calls with `axios` via the shared `api.ts` instance for consistency
- [ ] Ensure all services use the same error handling pattern (axios interceptors from `api.ts`)
- [ ] `src/services/budgetService.ts:26-27` — Fix inline param construction to use proper axios params object

### 3.7 Run TypeScript Compiler
- [ ] Run `tsc --noEmit` after all frontend changes to catch type errors
- [ ] Fix any errors surfaced by the compiler

---

## Phase 4: Testing & Verification

### 4.1 Existing Tests
- [ ] Run `python tests/test_budget_manager.py` to confirm no regressions from backend changes
- [ ] Fix any test failures

### 4.2 TypeScript Verification
- [ ] Run `npx tsc --noEmit` from `frontend/` to verify all TypeScript compiles cleanly
- [ ] Run `npm run build` from `frontend/` to verify production build succeeds

### 4.3 Smoke Test
- [ ] Start backend with `uvicorn backend.api:app --reload --port 8000` and confirm it boots without errors
- [ ] Verify `/health` endpoint responds
- [ ] Start frontend with `npm run dev` from `frontend/` and confirm it loads

---

## Notes

- **Credential rotation** is listed in Phase 1 but is a manual step the user must handle outside of code changes
- The `legacy/` directory is properly archived and doesn't need removal unless the user prefers a cleaner repo
- iOS code was not audited in depth — it appears properly structured but is a separate effort
- `chatService.ts` uses raw `fetch()` for SSE streaming, which may be intentional (axios doesn't natively support SSE) — investigate before replacing
