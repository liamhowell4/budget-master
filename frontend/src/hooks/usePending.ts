import { useState, useEffect, useCallback } from 'react'
import {
  getPendingExpenses,
  confirmPendingExpense,
  skipPendingExpense,
} from '@/services/budgetService'
import type { PendingExpense } from '@/types/recurring'

export function usePending() {
  const [pending, setPending] = useState<PendingExpense[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPending = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPendingExpenses()
      setPending(data.pending_expenses)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pending')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPending()
  }, [fetchPending])

  const confirm = useCallback(
    async (pendingId: string, adjustedAmount?: number) => {
      try {
        await confirmPendingExpense(pendingId, adjustedAmount)
        setPending((prev) => prev.filter((p) => p.pending_id !== pendingId))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to confirm')
        throw err
      }
    },
    []
  )

  const skip = useCallback(async (pendingId: string) => {
    try {
      await skipPendingExpense(pendingId)
      setPending((prev) => prev.filter((p) => p.pending_id !== pendingId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip')
      throw err
    }
  }, [])

  return { pending, loading, error, refetch: fetchPending, confirm, skip }
}
