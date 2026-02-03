# Custom Categories PRD

## Overview

Allow users to create, edit, and delete custom expense categories, replacing the current hardcoded 12-category system with a flexible per-user category model.

## Goals

1. **Personalization** — Users can define categories that match their spending habits
2. **Budget Control** — Category budgets are tied to a total monthly budget, preventing over-allocation
3. **Data Integrity** — Historical expenses remain valid when categories change
4. **Seamless AI Integration** — Claude recognizes and uses each user's custom categories

## Non-Goals

- Shared/family category management (future)
- Category templates or presets library (future)
- Import categories from other apps (future)

---

## User Stories

### New User Onboarding
> As a new user, I want to set my total monthly budget and customize my categories so the app matches how I think about my spending.

### Add Custom Category
> As a user, I want to create a new category (e.g., "Pet Supplies") with its own budget cap so I can track spending that doesn't fit existing categories.

### Edit Category
> As a user, I want to rename a category or change its icon/color so my dashboard reflects my preferences.

### Delete Category
> As a user, I want to remove a category I no longer use and reassign its historical expenses to another category.

### Budget Reallocation
> As a user, I want to adjust my category budgets knowing unused budget flows to "Other" and I can't exceed my total.

---

## Detailed Requirements

### Category Model

Each category has:

| Field | Type | Description |
|-------|------|-------------|
| `category_id` | string | Auto-generated UPPER_SNAKE_CASE (e.g., `PET_SUPPLIES`) |
| `display_name` | string | User-facing name (e.g., "Pet Supplies") |
| `icon` | string | Lucide icon name (e.g., `"dog"`, `"utensils"`) |
| `color` | string | Hex color code (e.g., `"#4F46E5"`) |
| `monthly_cap` | number | Budget cap for this category |
| `is_system` | boolean | `true` for OTHER (cannot be deleted) |
| `created_at` | timestamp | When category was created |
| `sort_order` | number | Display order in lists |

### Constraints

| Rule | Details |
|------|---------|
| Maximum categories | 15 (including OTHER) |
| Minimum categories | 1 (OTHER cannot be deleted) |
| Name uniqueness | No duplicate names per user (case-insensitive) |
| Name format | 1-30 characters, alphanumeric + spaces |
| ID generation | Uppercase, spaces → underscores, strip special chars |
| Budget cap | 0 ≤ cap ≤ remaining unallocated budget |

### The OTHER Category

- **Always exists** — Created automatically, cannot be deleted
- **Catch-all budget** — Receives unallocated budget from total
- **Catch-all expenses** — Default for expenses that don't fit elsewhere
- **System flag** — `is_system: true` prevents deletion in UI and API

### Budget Math

```
Total Monthly Budget = Sum of all category caps

When creating/editing a category:
  available_budget = total_budget - sum(other_category_caps)
  new_cap must be ≤ available_budget

OTHER.monthly_cap = total_budget - sum(non_other_caps)
```

**Example:**
- Total budget: $3,000
- FOOD_OUT cap: $500
- RENT cap: $1,400
- OTHER cap (auto-calculated): $1,100

If user creates new category with $200 cap:
- OTHER cap becomes: $900

If OTHER would become $0, user cannot create new categories until they:
1. Increase total budget, OR
2. Reduce another category's cap

---

## Onboarding Flow

### Trigger Conditions
- New user signup (required)
- Existing user with no `budget_caps` configured (guided)

### Steps

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Set Total Monthly Budget                           │
│  ─────────────────────────────────────────────────────────  │
│  "What's your total monthly budget?"                        │
│  [ $________ ]                                              │
│                                                             │
│  (Helper text: You can change this anytime in Settings)     │
│                                              [Continue →]   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Choose Your Categories                             │
│  ─────────────────────────────────────────────────────────  │
│  Start with our suggestions, then customize:                │
│                                                             │
│  ☑ Food & Dining      ☑ Rent/Mortgage    ☑ Utilities       │
│  ☑ Groceries          ☑ Transportation   ☑ Medical         │
│  ☐ Coffee             ☐ Tech             ☐ Travel          │
│  ☐ Hotels             ☐ Ride Share       ☑ Other (required)│
│                                                             │
│  [+ Add Custom Category]                                    │
│                                              [Continue →]   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Set Category Budgets                               │
│  ─────────────────────────────────────────────────────────  │
│  Total Budget: $3,000                                       │
│  Remaining to allocate: $400                                │
│                                                             │
│  🍽  Food & Dining     [ $500  ]  ━━━━━━━━━░░░░ 17%        │
│  🏠 Rent/Mortgage     [ $1,400 ]  ━━━━━━━━━━━━━━━░ 47%     │
│  ⚡ Utilities          [ $200  ]  ━━━░░░░░░░░░░░░ 7%        │
│  🛒 Groceries         [ $400  ]  ━━━━━━░░░░░░░░░ 13%       │
│  🚗 Transportation    [ $100  ]  ━━░░░░░░░░░░░░░ 3%        │
│  📦 Other             [ $400  ]  (auto-fills remainder)    │
│                                                             │
│  (Helper: "Other" receives your unallocated budget)        │
│                                              [Finish →]    │
└─────────────────────────────────────────────────────────────┘
```

### Post-Onboarding
- User lands on Dashboard
- Toast: "Setup complete! You can edit categories anytime in Settings."

---

## Category CRUD Operations

### Create Category

**Trigger:** User clicks "+ Add Category" in Settings or Onboarding

**Flow:**
1. Modal opens with form:
   - Name (required, validates uniqueness)
   - Icon picker (grid of Lucide icons)
   - Color picker (palette + custom option)
   - Budget cap (slider/input, max = unallocated budget)
2. On save:
   - Generate `category_id` from name
   - Validate constraints
   - Create in Firestore
   - Recalculate OTHER cap
   - Update Claude's category list (next request)

**Validation Errors:**
- "Category name already exists"
- "Maximum 15 categories reached"
- "Budget cap exceeds available budget ($X remaining)"

### Edit Category

**Editable fields:**
- `display_name` (with rename cascade)
- `icon`
- `color`
- `monthly_cap`
- `sort_order` (drag-and-drop reordering)

**Non-editable:**
- `category_id` (immutable after creation)
- `is_system` (cannot un-flag OTHER)

**Rename Cascade:**
When `display_name` changes:
1. Update category document
2. Update all expenses with this `category_id` (category_id stays same, just display changes)
3. Note: Since we use `category_id` as the key in expenses, no cascade needed for expenses — they reference the ID, not the name

### Delete Category

**Precondition:** Category is not OTHER (`is_system: false`)

**Flow:**
1. User clicks delete on category
2. Modal: "Delete [Category Name]?"
   - Show count of affected expenses
   - Dropdown: "Move expenses to: [Other categories...]"
   - Default selection: OTHER
3. On confirm:
   - Reassign all expenses to selected category
   - Delete category document
   - Recalculate OTHER cap (absorbs freed budget)

**Edge Cases:**
- Category has 0 expenses → Skip reassignment step
- User tries to delete OTHER → Button disabled, tooltip explains

---

## Technical Implementation

### Firebase Schema

**Collection:** `users/{userId}/categories`

```javascript
{
  category_id: "PET_SUPPLIES",          // Document ID
  display_name: "Pet Supplies",
  icon: "dog",
  color: "#8B5CF6",
  monthly_cap: 150.00,
  is_system: false,
  created_at: Timestamp,
  sort_order: 7
}
```

**OTHER document (auto-created):**
```javascript
{
  category_id: "OTHER",
  display_name: "Other",
  icon: "more-horizontal",
  color: "#6B7280",
  monthly_cap: 400.00,    // Auto-calculated
  is_system: true,
  created_at: Timestamp,
  sort_order: 999         // Always last
}
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories` | List user's categories |
| POST | `/categories` | Create new category |
| PUT | `/categories/{id}` | Update category |
| DELETE | `/categories/{id}` | Delete category (with reassignment) |
| PUT | `/categories/reorder` | Update sort order |
| GET | `/budget/total` | Get total monthly budget |
| PUT | `/budget/total` | Update total monthly budget |

### MCP Integration

**Client-side schema injection** (in `client.py`):

```python
# Fetch user's categories
user_categories = user_firebase.get_user_categories()
category_names = [cat["category_id"] for cat in user_categories]

# Patch tool schemas before sending to Claude
for tool in available_tools:
    if "category" in tool["input_schema"].get("properties", {}):
        tool["input_schema"]["properties"]["category"]["enum"] = category_names
```

**Server-side validation** (in `expense_server.py`):

```python
def get_user_category_enum(user_id: str):
    """Generate dynamic enum for validation"""
    firebase = FirebaseClient.for_user(user_id)
    categories = firebase.get_user_categories()
    return Enum('ExpenseType', {cat['category_id']: cat['display_name'] for cat in categories})

# In tool handlers:
UserExpenseType = get_user_category_enum(user_id)
try:
    category = UserExpenseType[category_str]
except KeyError:
    return error("Invalid category")
```

**System prompt injection** (in `system_prompts.py`):

```python
def get_expense_parsing_system_prompt(user_categories: list[dict]) -> str:
    category_list = "\n".join([
        f"- {cat['category_id']}: {cat['display_name']}"
        for cat in user_categories
    ])
    return f"""
    ...
    Valid categories for this user:
    {category_list}

    ALWAYS use one of these exact category IDs when saving expenses.
    ...
    """
```

### Migration Strategy

**For existing users:**

1. On login, check if `users/{userId}/categories` collection exists
2. If not, check if they have `budget_caps` configured
3. If no budget setup → Trigger onboarding flow
4. If has old budget_caps → Migrate:
   - Create category documents from ExpenseType enum
   - Copy existing caps
   - Calculate OTHER from remainder
   - Set `onboarding_complete: true`

**For existing expenses:**
- No migration needed — expenses already store category as string
- String matches `category_id`, which we're keeping as UPPER_SNAKE_CASE

---

## UI Components

### Settings > Categories Page

```
┌─────────────────────────────────────────────────────────────┐
│  Categories                                    [+ Add New]  │
│  ─────────────────────────────────────────────────────────  │
│  Drag to reorder • Click to edit                           │
│                                                             │
│  ≡ 🍽  Food & Dining        $500/mo           [Edit] [Del] │
│  ≡ 🏠 Rent                  $1,400/mo         [Edit] [Del] │
│  ≡ 🛒 Groceries            $400/mo           [Edit] [Del] │
│  ≡ 🐕 Pet Supplies          $150/mo           [Edit] [Del] │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  📦 Other                   $550/mo           [Edit]       │
│     (Catches unallocated budget - cannot be deleted)       │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│  Total Monthly Budget: $3,000          [Edit Total Budget] │
└─────────────────────────────────────────────────────────────┘
```

### Add/Edit Category Modal

```
┌─────────────────────────────────────────────────────────────┐
│  Add Category                                          [X]  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Name                                                       │
│  [ Pet Supplies                    ]                        │
│                                                             │
│  Icon                                                       │
│  ┌─────────────────────────────────┐                       │
│  │ 🐕 🐈 🦴 🐾 🐟 🐦 🦎 🐰 │  (Lucide icons)         │
│  │ 🏠 🚗 ✈️ 🍽 💊 ⚡ 🛒 ☕ │                           │
│  └─────────────────────────────────┘                       │
│                                                             │
│  Color                                                      │
│  ┌─────────────────────────────────┐                       │
│  │ ● ● ● ● ● ● ● ● │  [Custom...]                  │
│  └─────────────────────────────────┘                       │
│                                                             │
│  Monthly Budget Cap                                         │
│  [ $150        ]  of $550 available                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░                  │
│                                                             │
│                              [Cancel]  [Save Category]     │
└─────────────────────────────────────────────────────────────┘
```

### Delete Confirmation Modal

```
┌─────────────────────────────────────────────────────────────┐
│  Delete "Pet Supplies"?                                [X]  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  This category has 23 expenses totaling $487.50.           │
│                                                             │
│  Move these expenses to:                                    │
│  [ Other                          ▼]                        │
│                                                             │
│  The $150 budget cap will be added back to "Other".        │
│                                                             │
│                              [Cancel]  [Delete Category]   │
└─────────────────────────────────────────────────────────────┘
```

---

## Color Palette

Recommended preset colors (12 options):

| Name | Hex | Use Case |
|------|-----|----------|
| Red | `#EF4444` | Alerts, food |
| Orange | `#F97316` | Energy, utilities |
| Amber | `#F59E0B` | Warnings, coffee |
| Yellow | `#EAB308` | Highlights |
| Lime | `#84CC16` | Success, groceries |
| Green | `#22C55E` | Money, income |
| Teal | `#14B8A6` | Health, medical |
| Cyan | `#06B6D4` | Tech, digital |
| Blue | `#3B82F6` | Trust, rent |
| Indigo | `#6366F1` | Professional |
| Purple | `#8B5CF6` | Creative, pets |
| Pink | `#EC4899` | Personal |
| Gray | `#6B7280` | Other/default |

---

## Icon Set

Curated Lucide icons for category picker (~40 icons):

**Food & Drink:** `utensils`, `coffee`, `wine`, `pizza`, `sandwich`, `apple`, `cookie`

**Home:** `home`, `bed`, `sofa`, `lamp`, `key`

**Transport:** `car`, `fuel`, `bus`, `bike`, `plane`, `train`

**Shopping:** `shopping-cart`, `shopping-bag`, `shirt`, `gift`

**Health:** `heart-pulse`, `pill`, `stethoscope`, `dumbbell`

**Tech:** `laptop`, `smartphone`, `monitor`, `wifi`, `gamepad-2`

**Finance:** `wallet`, `credit-card`, `receipt`, `piggy-bank`

**Pets:** `dog`, `cat`, `fish`, `bird`

**Utilities:** `zap`, `droplet`, `flame`, `thermometer`

**Other:** `folder`, `tag`, `star`, `bookmark`, `more-horizontal`

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Users who complete onboarding | >90% |
| Users who create custom category | >30% within first month |
| Category-related support tickets | <5% of total |
| Avg categories per user | 6-10 |

---

## Open Questions

1. **Category sharing** — Future: Allow shared categories for family/couples accounts?
2. **Category suggestions** — Should Claude suggest creating a new category if it sees repeated "Other" expenses with similar names?
3. **Category insights** — Show spending trends per category over time?

---

## Appendix: Default Categories

Starting presets (user can remove all except OTHER):

| ID | Display Name | Icon | Default Color |
|----|--------------|------|---------------|
| FOOD_OUT | Food & Dining | `utensils` | #EF4444 |
| GROCERIES | Groceries | `shopping-cart` | #84CC16 |
| RENT | Rent/Mortgage | `home` | #3B82F6 |
| UTILITIES | Utilities | `zap` | #F97316 |
| GAS | Gas/Fuel | `fuel` | #F59E0B |
| TRANSPORTATION | Transportation | `car` | #6366F1 |
| MEDICAL | Medical/Health | `heart-pulse` | #14B8A6 |
| COFFEE | Coffee | `coffee` | #92400E |
| TECH | Tech/Electronics | `laptop` | #06B6D4 |
| TRAVEL | Travel | `plane` | #8B5CF6 |
| HOTEL | Hotels | `bed` | #EC4899 |
| RIDE_SHARE | Ride Share | `car` | #6366F1 |
| OTHER | Other | `more-horizontal` | #6B7280 |
