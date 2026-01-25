import { useState, useEffect, useCallback, useRef } from 'react'
import { getBudgetStatus } from '@/services/budgetService'
import type { BudgetStatus } from '@/types/budget'

// Session cache for budget - persists across component mounts
const budgetCache = new Map<string, BudgetStatus>()

function getCacheKey(year?: number, month?: number): string {
  return `${year ?? 'current'}-${month ?? 'current'}`
}

export function useBudget(year?: number, month?: number) {
  const cacheKey = getCacheKey(year, month)
  const cachedData = budgetCache.get(cacheKey)

  const [budget, setBudget] = useState<BudgetStatus | null>(cachedData ?? null)
  const [loading, setLoading] = useState(!cachedData)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef<string | null>(null)

  const fetchBudget = useCallback(async (forceRefresh = false) => {
    // Skip if already fetched this key (unless forcing refresh)
    if (!forceRefresh && fetchedRef.current === cacheKey && budgetCache.has(cacheKey)) {
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await getBudgetStatus(year, month)
      budgetCache.set(cacheKey, data)
      setBudget(data)
      fetchedRef.current = cacheKey
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load budget')
    } finally {
      setLoading(false)
    }
  }, [year, month, cacheKey])

  useEffect(() => {
    // If we have cached data, use it immediately
    if (cachedData) {
      setBudget(cachedData)
      setLoading(false)
      fetchedRef.current = cacheKey
      return
    }

    fetchBudget()
  }, [cacheKey, cachedData, fetchBudget])

  const refetch = useCallback(() => fetchBudget(true), [fetchBudget])

  return { budget, loading, error, refetch }
}

// Export function to invalidate cache (useful after adding/editing expenses)
export function invalidateBudgetCache(year?: number, month?: number) {
  if (year === undefined && month === undefined) {
    budgetCache.clear()
  } else {
    budgetCache.delete(getCacheKey(year, month))
  }
}
