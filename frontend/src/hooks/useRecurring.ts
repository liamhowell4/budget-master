import { useState, useEffect, useCallback } from 'react'
import { getRecurringExpenses, deleteRecurringExpense } from '@/services/recurringService'
import type { RecurringExpense } from '@/types/recurring'

export function useRecurring() {
  const [recurring, setRecurring] = useState<RecurringExpense[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRecurring = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getRecurringExpenses()
      setRecurring(data.recurring_expenses)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recurring expenses')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRecurring()
  }, [fetchRecurring])

  const deleteTemplate = useCallback(async (templateId: string) => {
    try {
      await deleteRecurringExpense(templateId)
      setRecurring((prev) => prev.filter((r) => r.template_id !== templateId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete')
      throw err
    }
  }, [])

  return { recurring, loading, error, refetch: fetchRecurring, deleteTemplate }
}
