import { useState, useEffect, useCallback, useRef } from 'react'
import { getExpenses } from '@/services/expenseService'
import type { Expense } from '@/types/expense'

// Session cache for expenses - persists across component mounts
const expensesCache = new Map<string, Expense[]>()

function getCacheKey(year?: number, month?: number, category?: string): string {
  return `${year ?? 'all'}-${month ?? 'all'}-${category ?? 'all'}`
}

export function useExpenses(year?: number, month?: number, category?: string) {
  const cacheKey = getCacheKey(year, month, category)
  const cachedData = expensesCache.get(cacheKey)

  const [expenses, setExpenses] = useState<Expense[]>(cachedData ?? [])
  const [loading, setLoading] = useState(!cachedData)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef<string | null>(null)

  const fetchExpenses = useCallback(async (forceRefresh = false) => {
    // Skip if already fetched this key (unless forcing refresh)
    if (!forceRefresh && fetchedRef.current === cacheKey && expensesCache.has(cacheKey)) {
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await getExpenses(year, month, category)
      expensesCache.set(cacheKey, data.expenses)
      setExpenses(data.expenses)
      fetchedRef.current = cacheKey
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load expenses')
    } finally {
      setLoading(false)
    }
  }, [year, month, category, cacheKey])

  useEffect(() => {
    // If we have cached data, use it immediately
    if (cachedData) {
      setExpenses(cachedData)
      setLoading(false)
      fetchedRef.current = cacheKey
      return
    }

    fetchExpenses()
  }, [cacheKey, cachedData, fetchExpenses])

  const refetch = useCallback(() => fetchExpenses(true), [fetchExpenses])

  return { expenses, loading, error, refetch }
}

// Export function to invalidate cache (useful after adding/editing expenses)
export function invalidateExpensesCache(year?: number, month?: number, category?: string) {
  if (year === undefined && month === undefined && category === undefined) {
    expensesCache.clear()
  } else {
    expensesCache.delete(getCacheKey(year, month, category))
  }
}
