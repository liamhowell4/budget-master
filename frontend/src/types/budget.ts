import type { ExpenseType } from './expense'

export interface BudgetCategory {
  category: ExpenseType
  spending: number
  cap: number
  percentage: number
  remaining: number
  icon?: string // Lucide icon name
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
}

export interface BudgetCapsUpdate {
  total_budget: number
  category_budgets: Record<ExpenseType, number>
}

export interface BudgetCapsResponse {
  success: boolean
  message: string
  updated_caps: Record<string, number>
}
