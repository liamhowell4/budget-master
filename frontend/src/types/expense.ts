// Legacy ExpenseType for backward compatibility
// With custom categories, category can be any string
export const ExpenseType = {
  FOOD_OUT: 'FOOD_OUT',
  COFFEE: 'COFFEE',
  GROCERIES: 'GROCERIES',
  RENT: 'RENT',
  UTILITIES: 'UTILITIES',
  MEDICAL: 'MEDICAL',
  GAS: 'GAS',
  RIDE_SHARE: 'RIDE_SHARE',
  HOTEL: 'HOTEL',
  TECH: 'TECH',
  TRAVEL: 'TRAVEL',
  OTHER: 'OTHER',
} as const

export type ExpenseType = (typeof ExpenseType)[keyof typeof ExpenseType] | string

export interface ExpenseDate {
  day: number
  month: number
  year: number
}

export interface Expense {
  id: string
  expense_name: string
  amount: number
  date: ExpenseDate
  category: string  // Changed to string to support custom categories
  timestamp?: string
  input_type?: 'mcp' | 'recurring'
}

export interface ExpensesResponse {
  year: number
  month: number
  category?: string
  count: number
  expenses: Expense[]
}
