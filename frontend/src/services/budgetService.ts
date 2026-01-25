import api from './api'
import type { BudgetStatus } from '@/types/budget'
import type { PendingListResponse } from '@/types/recurring'

export async function getBudgetStatus(
  year?: number,
  month?: number
): Promise<BudgetStatus> {
  const params = new URLSearchParams()
  if (year) params.append('year', year.toString())
  if (month) params.append('month', month.toString())

  const response = await api.get<BudgetStatus>(`/budget?${params}`)
  return response.data
}

export async function getPendingExpenses(): Promise<PendingListResponse> {
  const response = await api.get<PendingListResponse>('/pending')
  return response.data
}

export async function confirmPendingExpense(
  pendingId: string,
  adjustedAmount?: number
): Promise<{ success: boolean; expense_id: string; message: string }> {
  const params = adjustedAmount ? `?adjusted_amount=${adjustedAmount}` : ''
  const response = await api.post(`/pending/${pendingId}/confirm${params}`)
  return response.data
}

export async function skipPendingExpense(
  pendingId: string
): Promise<{ success: boolean; message: string }> {
  const response = await api.delete(`/pending/${pendingId}`)
  return response.data
}
