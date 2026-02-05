import { useState, useEffect, useCallback } from 'react'
import { categoryService } from '@/services/categoryService'

interface UseOnboardingCheckReturn {
  needsOnboarding: boolean | null
  loading: boolean
  recheckOnboarding: () => Promise<void>
}

/**
 * Hook to check if the user needs to complete onboarding.
 *
 * Onboarding is needed when:
 * - Total monthly budget is 0, OR
 * - All category caps sum to 0
 */
export function useOnboardingCheck(): UseOnboardingCheckReturn {
  const [needsOnboarding, setNeedsOnboarding] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)

  const checkOnboarding = useCallback(async () => {
    try {
      setLoading(true)
      const data = await categoryService.getCategories()

      const totalBudget = data.total_monthly_budget
      const allocatedSum = data.categories.reduce(
        (sum, cat) => sum + (cat.monthly_cap || 0),
        0
      )

      // Needs onboarding if no budget set or no allocations
      setNeedsOnboarding(totalBudget === 0 || allocatedSum === 0)
    } catch (err) {
      console.error('Error checking onboarding status:', err)
      // On error, assume no onboarding needed to avoid blocking the app
      setNeedsOnboarding(false)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkOnboarding()
  }, [checkOnboarding])

  return {
    needsOnboarding,
    loading,
    recheckOnboarding: checkOnboarding,
  }
}

export default useOnboardingCheck
