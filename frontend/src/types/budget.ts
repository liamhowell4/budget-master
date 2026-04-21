export interface BudgetCategory {
  category: string  // Category ID (e.g., "FOOD_OUT" or custom)
  spending: number
  cap: number
  percentage: number
  remaining: number
  icon?: string // Lucide icon name
  color?: string // Hex color
  display_name?: string // Display name from custom category
}

export interface BudgetStatus {
  year: number
  month: number
  month_name: string
  categories: BudgetCategory[]
  total_spending: number
  total_cap: number
  total_percentage: number
  total_remaining: number
  excluded_categories: string[]  // Category IDs excluded from total calculation
  period_start: string      // ISO date
  period_end: string        // ISO date
  period_label: string      // "Mar 15 – Apr 14, 2026"
  days_in_period: number
  days_elapsed: number
  monthly_total_cap: number // Original monthly cap for reference
}

export interface BudgetCapsUpdate {
  total_budget: number
  category_budgets: Record<string, number>
}

export interface BudgetCapsResponse {
  success: boolean
  message: string
  updated_caps: Record<string, number>
}
