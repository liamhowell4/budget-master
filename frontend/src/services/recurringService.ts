import api from './api'
import type { RecurringListResponse } from '@/types/recurring'

export async function getRecurringExpenses(): Promise<RecurringListResponse> {
  const response = await api.get<RecurringListResponse>('/recurring')
  return response.data
}

export async function deleteRecurringExpense(
  templateId: string
): Promise<{ success: boolean; message: string }> {
  const response = await api.delete(`/recurring/${templateId}`)
  return response.data
}
