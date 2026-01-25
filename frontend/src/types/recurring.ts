import type { ExpenseDate, ExpenseType } from './expense'

export type Frequency = 'monthly' | 'weekly' | 'biweekly'

export interface RecurringExpense {
  template_id: string
  expense_name: string
  amount: number
  category: ExpenseType
  frequency: Frequency
  day_of_month?: number | null
  day_of_week?: number | null
  last_of_month: boolean
  last_reminded?: ExpenseDate | null
  last_user_action?: ExpenseDate | null
  active: boolean
}

export interface PendingExpense {
  pending_id: string
  template_id: string
  expense_name: string
  amount: number
  date: ExpenseDate
  category: ExpenseType
  awaiting_confirmation: boolean
  created_at?: string
}

export interface RecurringListResponse {
  recurring_expenses: RecurringExpense[]
}

export interface PendingListResponse {
  pending_expenses: PendingExpense[]
}
