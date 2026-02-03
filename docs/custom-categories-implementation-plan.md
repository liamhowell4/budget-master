# Custom Categories Implementation Plan

## Overview

This document outlines the technical implementation steps for the Custom Categories feature. Work is organized into phases that can be completed incrementally.

**Estimated Scope:** ~15-20 files modified, ~1500-2000 lines of code

---

## Phase 1: Data Layer Foundation

**Goal:** Establish the new category data model without breaking existing functionality.

### 1.1 Firebase Schema Setup

**File:** `backend/firebase_client.py`

Add new methods:

```python
# Category CRUD
def get_user_categories(self) -> list[dict]
def get_category(self, category_id: str) -> dict | None
def create_category(self, category: dict) -> str
def update_category(self, category_id: str, updates: dict) -> bool
def delete_category(self, category_id: str) -> bool
def reorder_categories(self, order: list[str]) -> bool

# Budget helpers
def get_total_monthly_budget(self) -> float
def set_total_monthly_budget(self, amount: float) -> bool
def recalculate_other_cap(self) -> float

# Migration helpers
def has_categories_setup(self) -> bool
def initialize_default_categories(self, total_budget: float, selected_categories: list[str]) -> bool
```

**Collection:** `users/{userId}/categories/{category_id}`

**Tasks:**
- [ ] Create `Category` Pydantic model in `output_schemas.py`
- [ ] Implement `get_user_categories()` — returns all categories sorted by `sort_order`
- [ ] Implement `create_category()` — validates constraints, auto-generates ID
- [ ] Implement `update_category()` — handles cap recalculation
- [ ] Implement `delete_category()` — includes expense reassignment
- [ ] Implement `recalculate_other_cap()` — called after any cap change
- [ ] Implement `initialize_default_categories()` — for onboarding
- [ ] Add `has_categories_setup()` check for migration flow

### 1.2 Update Output Schemas

**File:** `backend/output_schemas.py`

```python
class Category(BaseModel):
    category_id: str  # UPPER_SNAKE_CASE
    display_name: str
    icon: str  # Lucide icon name
    color: str  # Hex code
    monthly_cap: float
    is_system: bool = False
    sort_order: int = 0

class CategoryCreate(BaseModel):
    display_name: str  # 1-30 chars
    icon: str
    color: str
    monthly_cap: float  # >= 0

class CategoryUpdate(BaseModel):
    display_name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    monthly_cap: Optional[float] = None
    sort_order: Optional[int] = None
```

**Tasks:**
- [ ] Add `Category`, `CategoryCreate`, `CategoryUpdate` models
- [ ] Add `generate_category_id(display_name: str) -> str` helper function
- [ ] Keep `ExpenseType` enum for now (backward compatibility during migration)

### 1.3 Seed Script Update

**File:** `scripts/seed_firestore.py`

**Tasks:**
- [ ] Add function to seed default categories for a user
- [ ] Include icon and color mappings for the 12 presets
- [ ] Create OTHER as system category

---

## Phase 2: API Endpoints

**Goal:** Expose category management via REST API.

### 2.1 Category Endpoints

**File:** `backend/api.py`

```python
@app.get("/categories")
async def get_categories(current_user: AuthenticatedUser = Depends(get_current_user)):
    """List all categories for the authenticated user."""

@app.post("/categories")
async def create_category(
    category: CategoryCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new category."""

@app.put("/categories/{category_id}")
async def update_category(
    category_id: str,
    updates: CategoryUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a category."""

@app.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    reassign_to: str = Query(..., description="Category ID to reassign expenses to"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a category and reassign its expenses."""

@app.put("/categories/reorder")
async def reorder_categories(
    order: list[str],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update category sort order."""
```

### 2.2 Budget Endpoints

**File:** `backend/api.py`

```python
@app.get("/budget/total")
async def get_total_budget(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get user's total monthly budget."""

@app.put("/budget/total")
async def set_total_budget(
    amount: float,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Set total monthly budget (recalculates OTHER)."""
```

### 2.3 Onboarding Endpoint

**File:** `backend/api.py`

```python
@app.get("/onboarding/status")
async def get_onboarding_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Check if user needs onboarding."""

@app.post("/onboarding/complete")
async def complete_onboarding(
    total_budget: float,
    categories: list[CategoryCreate],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Complete onboarding with initial budget and categories."""
```

**Tasks:**
- [ ] Implement all endpoints with proper validation
- [ ] Add validation: max 15 categories
- [ ] Add validation: unique names (case-insensitive)
- [ ] Add validation: cap <= available budget
- [ ] Add validation: cannot delete OTHER
- [ ] Add validation: name 1-30 chars, alphanumeric + spaces
- [ ] Return proper error messages for all validation failures

---

## Phase 3: MCP Integration

**Goal:** Make Claude aware of user's custom categories.

### 3.1 Client-Side Schema Modification

**File:** `backend/mcp/client.py`

Modify `process_expense_message()`:

```python
async def process_expense_message(self, ...):
    # ... existing code ...

    # Fetch user's categories
    user_categories = user_firebase.get_user_categories()
    category_ids = [cat["category_id"] for cat in user_categories]

    # Get tools and patch schemas
    response = await self.client.session.list_tools()
    available_tools = []
    for tool in response.tools:
        schema = copy.deepcopy(tool.inputSchema)
        # Patch category enum in any tool that has it
        if "properties" in schema and "category" in schema["properties"]:
            schema["properties"]["category"]["enum"] = category_ids
        available_tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": schema
        })

    # ... rest of method ...
```

**Tasks:**
- [ ] Import `copy` module
- [ ] Fetch user categories before building tool list
- [ ] Deep copy schemas to avoid mutation
- [ ] Patch `category` enum in all relevant tools
- [ ] Add user categories to system prompt (see 3.2)

### 3.2 Dynamic System Prompts

**File:** `backend/system_prompts.py`

```python
def get_expense_parsing_system_prompt(user_categories: list[dict] = None) -> str:
    """
    Generate system prompt with user's categories.

    Args:
        user_categories: List of category dicts with category_id and display_name
    """
    if user_categories:
        category_list = "\n".join([
            f"- {cat['category_id']}: {cat['display_name']}"
            for cat in user_categories
        ])
    else:
        # Fallback to hardcoded list (for backward compatibility)
        category_list = "..."  # existing hardcoded list

    return f"""
    ...existing prompt...

    ## Valid Categories

    This user has the following expense categories:
    {category_list}

    IMPORTANT: You MUST use one of these exact category IDs (the UPPER_SNAKE_CASE key,
    not the display name) when calling save_expense, update_expense, or any tool
    that requires a category.

    ...rest of prompt...
    """
```

**Tasks:**
- [ ] Update `get_expense_parsing_system_prompt()` to accept categories parameter
- [ ] Format categories clearly for Claude
- [ ] Update call site in `client.py` to pass user categories

### 3.3 Server-Side Validation

**File:** `backend/mcp/expense_server.py`

Replace static `ExpenseType` validation with dynamic validation:

```python
def validate_category(category_str: str, user_id: str) -> bool:
    """Validate category exists for user."""
    firebase = FirebaseClient.for_user(user_id)
    categories = firebase.get_user_categories()
    valid_ids = [cat["category_id"] for cat in categories]
    return category_str in valid_ids

# In _save_expense:
async def _save_expense(arguments: dict) -> list[TextContent]:
    user_id = verify_token_and_get_uid(arguments["auth_token"])
    category_str = arguments["category"]

    if not validate_category(category_str, user_id):
        return [TextContent(
            type="text",
            text=f"Error: Invalid category '{category_str}'. Use get_categories to see valid options."
        )]

    # ... rest of function (no longer needs ExpenseType enum)
```

**Tasks:**
- [ ] Create `validate_category(category_str, user_id)` helper
- [ ] Update `_save_expense` to use dynamic validation
- [ ] Update `_update_expense` to use dynamic validation
- [ ] Update `_get_budget_status` to use dynamic validation
- [ ] Update `_create_recurring_expense` to use dynamic validation
- [ ] Update `_get_recent_expenses` category filter
- [ ] Update `_search_expenses` category filter
- [ ] Update `_query_expenses` category filter
- [ ] Update `_get_budget_remaining` to iterate user's categories
- [ ] Update `_compare_periods` category filter
- [ ] Update `_get_largest_expenses` category filter
- [ ] Update `_get_categories` to return user's categories (not hardcoded)

### 3.4 Update get_categories Tool

**File:** `backend/mcp/expense_server.py`

```python
async def _get_categories(arguments: dict) -> list[TextContent]:
    """Get user's expense categories."""
    user_id = verify_token_and_get_uid(arguments["auth_token"])
    firebase = FirebaseClient.for_user(user_id)
    categories = firebase.get_user_categories()

    result = [{
        "key": cat["category_id"],
        "name": cat["display_name"],
        "icon": cat["icon"],
        "color": cat["color"]
    } for cat in categories]

    return [TextContent(type="text", text=json.dumps({"categories": result}))]
```

**Tasks:**
- [ ] Update `_get_categories` to fetch from user's collection
- [ ] Update tool schema to require `auth_token`
- [ ] Return icon and color in response

---

## Phase 4: Budget Manager Updates

**Goal:** Make budget calculations work with dynamic categories.

### 4.1 Refactor Budget Manager

**File:** `backend/budget_manager.py`

```python
class BudgetManager:
    def __init__(self, firebase: FirebaseClient):
        self.firebase = firebase

    def calculate_monthly_spending(self, category_id: str, year: int, month: int) -> float:
        """Calculate spending for a category (now uses string ID, not enum)."""
        # ... implementation stays similar, just uses string instead of enum

    def get_budget_warning(self, category_id: str, amount: float, year: int, month: int) -> str:
        """Get budget warning for a category."""
        # Fetch category cap from user's categories
        category = self.firebase.get_category(category_id)
        if not category:
            return ""
        cap = category.get("monthly_cap", 0)
        # ... rest of warning logic
```

**Tasks:**
- [ ] Change `category: ExpenseType` parameters to `category_id: str`
- [ ] Fetch caps from user's categories collection
- [ ] Update warning logic to work with dynamic categories
- [ ] Update total budget calculation to sum user's category caps

---

## Phase 5: Frontend Implementation

**Goal:** Build the category management UI.

### 5.1 API Service

**File:** `frontend/src/services/api.ts`

```typescript
// Category types
interface Category {
  category_id: string;
  display_name: string;
  icon: string;
  color: string;
  monthly_cap: number;
  is_system: boolean;
  sort_order: number;
}

interface CategoryCreate {
  display_name: string;
  icon: string;
  color: string;
  monthly_cap: number;
}

// API methods
export const categoryApi = {
  getCategories: () => api.get<Category[]>('/categories'),
  createCategory: (data: CategoryCreate) => api.post<Category>('/categories', data),
  updateCategory: (id: string, data: Partial<CategoryCreate>) =>
    api.put<Category>(`/categories/${id}`, data),
  deleteCategory: (id: string, reassignTo: string) =>
    api.delete(`/categories/${id}?reassign_to=${reassignTo}`),
  reorderCategories: (order: string[]) =>
    api.put('/categories/reorder', { order }),
};

export const budgetApi = {
  getTotalBudget: () => api.get<{ total: number }>('/budget/total'),
  setTotalBudget: (amount: number) => api.put('/budget/total', { amount }),
};

export const onboardingApi = {
  getStatus: () => api.get<{ needs_onboarding: boolean }>('/onboarding/status'),
  complete: (data: { total_budget: number; categories: CategoryCreate[] }) =>
    api.post('/onboarding/complete', data),
};
```

**Tasks:**
- [ ] Add TypeScript interfaces for Category types
- [ ] Implement category API methods
- [ ] Implement budget API methods
- [ ] Implement onboarding API methods

### 5.2 Category Context

**File:** `frontend/src/contexts/CategoryContext.tsx` (new file)

```typescript
interface CategoryContextType {
  categories: Category[];
  loading: boolean;
  error: string | null;
  totalBudget: number;
  availableBudget: number;
  refreshCategories: () => Promise<void>;
  createCategory: (data: CategoryCreate) => Promise<void>;
  updateCategory: (id: string, data: Partial<CategoryCreate>) => Promise<void>;
  deleteCategory: (id: string, reassignTo: string) => Promise<void>;
  reorderCategories: (order: string[]) => Promise<void>;
  setTotalBudget: (amount: number) => Promise<void>;
}
```

**Tasks:**
- [ ] Create CategoryContext and provider
- [ ] Implement all CRUD operations with optimistic updates
- [ ] Calculate `availableBudget` (total - sum of non-OTHER caps)
- [ ] Handle loading and error states
- [ ] Auto-refresh on auth changes

### 5.3 Onboarding Flow

**Files:**
- `frontend/src/pages/Onboarding.tsx` (new)
- `frontend/src/components/onboarding/BudgetStep.tsx` (new)
- `frontend/src/components/onboarding/CategorySelectStep.tsx` (new)
- `frontend/src/components/onboarding/CategoryBudgetStep.tsx` (new)

**Tasks:**
- [ ] Create multi-step onboarding wizard
- [ ] Step 1: Total budget input with validation
- [ ] Step 2: Category selection (checkboxes for presets + custom)
- [ ] Step 3: Budget allocation with visual sliders
- [ ] Show remaining/unallocated budget prominently
- [ ] Add "Add Custom Category" inline flow
- [ ] Persist progress (in case of page reload)
- [ ] Redirect to dashboard on completion

### 5.4 Settings > Categories Page

**File:** `frontend/src/pages/Settings/Categories.tsx` (new or extend existing)

**Tasks:**
- [ ] List all categories with drag-and-drop reordering
- [ ] Show icon, name, color, budget cap for each
- [ ] Edit button opens modal
- [ ] Delete button (disabled for OTHER) opens confirmation
- [ ] "+ Add Category" button
- [ ] Show total budget and "Edit Total Budget" option
- [ ] Visual indicator when OTHER has $0 (can't add more)

### 5.5 Category Modal (Add/Edit)

**File:** `frontend/src/components/categories/CategoryModal.tsx` (new)

**Tasks:**
- [ ] Form with name, icon picker, color picker, budget cap
- [ ] Icon picker: Grid of ~40 curated Lucide icons
- [ ] Color picker: Preset palette (12 colors) + custom option
- [ ] Budget cap: Input with max = available budget
- [ ] Real-time validation with error messages
- [ ] Loading state during save

### 5.6 Delete Confirmation Modal

**File:** `frontend/src/components/categories/DeleteCategoryModal.tsx` (new)

**Tasks:**
- [ ] Show expense count and total for category
- [ ] Dropdown to select reassignment target
- [ ] Warning text about budget reallocation
- [ ] Confirm/Cancel buttons

### 5.7 Icon Picker Component

**File:** `frontend/src/components/ui/IconPicker.tsx` (new)

**Tasks:**
- [ ] Grid layout of Lucide icons
- [ ] Search/filter functionality (optional)
- [ ] Selected state styling
- [ ] Grouped by type (Food, Home, Transport, etc.)

### 5.8 Color Picker Component

**File:** `frontend/src/components/ui/ColorPicker.tsx` (new)

**Tasks:**
- [ ] Preset palette (12-16 colors)
- [ ] Custom color option (opens native picker or hex input)
- [ ] Selected state with checkmark
- [ ] Preview of selected color

### 5.9 Update Existing Components

**Files to update:**
- `frontend/src/pages/Dashboard.tsx` — Use dynamic categories for charts
- `frontend/src/pages/Expenses.tsx` — Use dynamic categories for filters
- `frontend/src/components/chat/` — Category dropdowns use dynamic list
- Any hardcoded `ExpenseType` references

**Tasks:**
- [ ] Replace hardcoded category lists with `useCategories()` hook
- [ ] Update category dropdowns/selects
- [ ] Update dashboard charts to show user's categories
- [ ] Update expense filters

---

## Phase 6: Migration & Cleanup

**Goal:** Migrate existing users and remove legacy code.

### 6.1 Migration Logic

**File:** `backend/firebase_client.py`

```python
def migrate_user_to_custom_categories(self) -> bool:
    """
    Migrate existing user from old budget_caps to new categories system.
    Called on login if user has old-style data.
    """
    # Check if already migrated
    if self.has_categories_setup():
        return True

    # Get existing budget caps (old style)
    old_caps = self._get_old_budget_caps()
    if not old_caps:
        return False  # Needs onboarding

    # Create categories from old caps
    total = 0
    for category_key, cap in old_caps.items():
        if category_key == "TOTAL":
            continue
        self.create_category({
            "category_id": category_key,
            "display_name": self._get_default_display_name(category_key),
            "icon": self._get_default_icon(category_key),
            "color": self._get_default_color(category_key),
            "monthly_cap": cap,
            "is_system": category_key == "OTHER"
        })
        if category_key != "OTHER":
            total += cap

    # Ensure OTHER exists
    if "OTHER" not in old_caps:
        self.create_category({
            "category_id": "OTHER",
            "display_name": "Other",
            "icon": "more-horizontal",
            "color": "#6B7280",
            "monthly_cap": 0,
            "is_system": True
        })

    # Set total budget
    self.set_total_monthly_budget(old_caps.get("TOTAL", total))

    return True
```

**Tasks:**
- [ ] Implement migration function
- [ ] Add default display names, icons, colors for preset categories
- [ ] Call migration on user login (in auth flow)
- [ ] Log migration events for monitoring

### 6.2 Remove Legacy Code

**Tasks:**
- [ ] Remove `ExpenseType` enum from `output_schemas.py` (after all references updated)
- [ ] Remove hardcoded category lists from `system_prompts.py`
- [ ] Remove old `seed_categories()` that used global categories
- [ ] Update `seed_firestore.py` to work with new per-user model
- [ ] Remove any unused category-related code

### 6.3 Update Tests

**File:** `tests/test_budget_manager.py` and new test files

**Tasks:**
- [ ] Update existing budget tests to use dynamic categories
- [ ] Add tests for category CRUD operations
- [ ] Add tests for budget cap constraints
- [ ] Add tests for category deletion with expense reassignment
- [ ] Add tests for migration logic
- [ ] Add tests for MCP schema patching

---

## Implementation Order

Recommended order to minimize risk and enable incremental testing:

```
Week 1: Foundation
├── Phase 1.1: Firebase schema + methods
├── Phase 1.2: Output schemas
└── Phase 2.1-2.2: Basic API endpoints

Week 2: Backend Integration
├── Phase 3.1: Client-side schema modification
├── Phase 3.2: Dynamic system prompts
├── Phase 3.3-3.4: Server-side validation
└── Phase 4: Budget manager updates

Week 3: Frontend Core
├── Phase 5.1: API service
├── Phase 5.2: Category context
├── Phase 5.4-5.6: Settings page + modals
└── Phase 5.7-5.8: Icon/color pickers

Week 4: Onboarding & Polish
├── Phase 5.3: Onboarding flow
├── Phase 5.9: Update existing components
├── Phase 6.1: Migration logic
└── Phase 6.2-6.3: Cleanup + tests
```

---

## Testing Checklist

### Unit Tests
- [ ] `generate_category_id()` produces valid UPPER_SNAKE_CASE
- [ ] Budget cap validation (0 ≤ cap ≤ available)
- [ ] Category name validation (length, characters, uniqueness)
- [ ] OTHER cannot be deleted
- [ ] Max 15 categories enforced

### Integration Tests
- [ ] Create category → appears in MCP tools
- [ ] Delete category → expenses reassigned
- [ ] Update cap → OTHER recalculated
- [ ] Claude uses correct categories in save_expense

### E2E Tests
- [ ] New user completes onboarding
- [ ] Existing user sees migration
- [ ] Add custom category flow
- [ ] Delete category with reassignment
- [ ] Budget slider constraints work

---

## Rollback Plan

If issues arise after deployment:

1. **Feature flag:** Add `CUSTOM_CATEGORIES_ENABLED` env var
2. **Fallback:** If disabled, use hardcoded `ExpenseType` enum
3. **Data safe:** Old expenses still work (category stored as string)
4. **Migration reversible:** Old `budget_caps` collection preserved

---

## Dependencies

| Dependency | Purpose | Already Installed? |
|------------|---------|-------------------|
| lucide-react | Icons | Yes |
| react-beautiful-dnd | Drag-drop reorder | No (or use native HTML5 DnD) |
| react-colorful | Color picker | No (or use native input[type=color]) |

**Recommendation:** Try native HTML5 drag-and-drop and `<input type="color">` first to avoid new dependencies.

---

## Files Changed Summary

### Backend (Python)
| File | Changes |
|------|---------|
| `backend/output_schemas.py` | Add Category models |
| `backend/firebase_client.py` | Add category CRUD methods |
| `backend/api.py` | Add category/budget/onboarding endpoints |
| `backend/mcp/client.py` | Patch tool schemas with user categories |
| `backend/mcp/expense_server.py` | Dynamic category validation |
| `backend/system_prompts.py` | Accept categories parameter |
| `backend/budget_manager.py` | Use string category IDs |
| `scripts/seed_firestore.py` | Update seeding logic |

### Frontend (TypeScript/React)
| File | Changes |
|------|---------|
| `frontend/src/services/api.ts` | Add category API methods |
| `frontend/src/contexts/CategoryContext.tsx` | New context |
| `frontend/src/pages/Onboarding.tsx` | New page |
| `frontend/src/pages/Settings/Categories.tsx` | New/updated page |
| `frontend/src/components/categories/*.tsx` | New components |
| `frontend/src/components/ui/IconPicker.tsx` | New component |
| `frontend/src/components/ui/ColorPicker.tsx` | New component |
| `frontend/src/pages/Dashboard.tsx` | Use dynamic categories |
| `frontend/src/pages/Expenses.tsx` | Use dynamic categories |

### Tests
| File | Changes |
|------|---------|
| `tests/test_budget_manager.py` | Update for dynamic categories |
| `tests/test_categories.py` | New test file |
| `tests/test_api_categories.py` | New test file |
