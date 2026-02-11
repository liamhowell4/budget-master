import api from './api'
import type { ExpensesResponse } from '@/types/expense'

export async function getExpenses(
  year?: number,
  month?: number,
  category?: string
): Promise<ExpensesResponse> {
  const params = new URLSearchParams()
  if (year) params.append('year', year.toString())
  if (month) params.append('month', month.toString())
  if (category) params.append('category', category)

  const response = await api.get<ExpensesResponse>(`/expenses?${params}`)
  return response.data
}

export async function verifyExpenses(expenseIds: string[]): Promise<string[]> {
  const response = await api.post<{ existing_ids: string[] }>('/expenses/verify', {
    expense_ids: expenseIds,
  })
  return response.data.existing_ids
}

interface DeleteExpenseResponse {
  success: boolean
  expense_id: string
}

export async function deleteExpense(expenseId: string): Promise<DeleteExpenseResponse> {
  const response = await api.delete<DeleteExpenseResponse>(`/expenses/${expenseId}`)
  return response.data
}

interface UpdateExpenseResponse {
  success: boolean
  expense_id: string
  updated_fields: {
    expense_name?: string
    amount?: number
    category?: string
  }
}

export async function updateExpense(
  expenseId: string,
  updates: { expense_name?: string; amount?: number; category?: string }
): Promise<UpdateExpenseResponse> {
  const response = await api.put<UpdateExpenseResponse>(`/expenses/${expenseId}`, updates)
  return response.data
}
