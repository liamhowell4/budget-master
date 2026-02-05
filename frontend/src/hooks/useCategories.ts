import { useState, useEffect, useCallback } from 'react'
import { categoryService } from '@/services/categoryService'
import type { Category, CategoryCreate, CategoryUpdate } from '@/types/category'

interface UseCategoriesReturn {
  categories: Category[]
  totalMonthlyBudget: number
  maxCategories: number
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  createCategory: (data: CategoryCreate) => Promise<{ success: boolean; category_id?: string; error?: string }>
  updateCategory: (
    categoryId: string,
    data: CategoryUpdate
  ) => Promise<{ success: boolean; error?: string }>
  deleteCategory: (
    categoryId: string,
    reassignTo?: string
  ) => Promise<{ success: boolean; reassigned_count?: number; error?: string }>
  reorderCategories: (categoryIds: string[]) => Promise<{ success: boolean; error?: string }>
  updateTotalBudget: (amount: number) => Promise<{ success: boolean; error?: string }>
  getAllocatedBudget: () => number
  getAvailableBudget: () => number
}

export function useCategories(): UseCategoriesReturn {
  const [categories, setCategories] = useState<Category[]>([])
  const [totalMonthlyBudget, setTotalMonthlyBudget] = useState(0)
  const [maxCategories, setMaxCategories] = useState(15)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchCategories = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await categoryService.getCategories()
      setCategories(response.categories)
      setTotalMonthlyBudget(response.total_monthly_budget)
      setMaxCategories(response.max_categories)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load categories'
      setError(errorMessage)
      console.error('Error fetching categories:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  // Listen for onboarding completion to refetch data
  useEffect(() => {
    const handleOnboardingComplete = () => {
      fetchCategories()
    }
    window.addEventListener('onboarding-complete', handleOnboardingComplete)
    return () => {
      window.removeEventListener('onboarding-complete', handleOnboardingComplete)
    }
  }, [fetchCategories])

  const createCategory = useCallback(
    async (data: CategoryCreate) => {
      try {
        const response = await categoryService.createCategory(data)
        if (response.success) {
          await fetchCategories() // Refetch to get updated list
          return { success: true, category_id: response.category_id }
        }
        return { success: false, error: 'Failed to create category' }
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to create category'
        return { success: false, error: errorMessage }
      }
    },
    [fetchCategories]
  )

  const updateCategory = useCallback(
    async (categoryId: string, data: CategoryUpdate) => {
      try {
        const response = await categoryService.updateCategory(categoryId, data)
        if (response.success) {
          await fetchCategories() // Refetch to get updated list
          return { success: true }
        }
        return { success: false, error: 'Failed to update category' }
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to update category'
        return { success: false, error: errorMessage }
      }
    },
    [fetchCategories]
  )

  const deleteCategory = useCallback(
    async (categoryId: string, reassignTo: string = 'OTHER') => {
      try {
        const response = await categoryService.deleteCategory(categoryId, reassignTo)
        if (response.success) {
          await fetchCategories() // Refetch to get updated list
          return { success: true, reassigned_count: response.reassigned_count }
        }
        return { success: false, error: 'Failed to delete category' }
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete category'
        return { success: false, error: errorMessage }
      }
    },
    [fetchCategories]
  )

  const reorderCategories = useCallback(
    async (categoryIds: string[]) => {
      try {
        // Optimistically update local state
        const newOrder = categoryIds.map((id, index) => {
          const cat = categories.find((c) => c.category_id === id)
          return cat ? { ...cat, sort_order: index } : null
        }).filter(Boolean) as Category[]

        setCategories(newOrder)

        const response = await categoryService.reorderCategories(categoryIds)
        if (!response.success) {
          await fetchCategories() // Revert on failure
          return { success: false, error: 'Failed to reorder categories' }
        }
        return { success: true }
      } catch (err: any) {
        await fetchCategories() // Revert on error
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to reorder categories'
        return { success: false, error: errorMessage }
      }
    },
    [categories, fetchCategories]
  )

  const updateTotalBudget = useCallback(
    async (amount: number) => {
      try {
        const response = await categoryService.updateTotalBudget(amount)
        if (response.success) {
          setTotalMonthlyBudget(response.total_monthly_budget)
          await fetchCategories() // Refetch to get updated OTHER cap
          return { success: true }
        }
        return { success: false, error: 'Failed to update total budget' }
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to update total budget'
        return { success: false, error: errorMessage }
      }
    },
    [fetchCategories]
  )

  const getAllocatedBudget = useCallback(() => {
    return categories.reduce((sum, cat) => sum + (cat.monthly_cap || 0), 0)
  }, [categories])

  const getAvailableBudget = useCallback(() => {
    return totalMonthlyBudget - getAllocatedBudget()
  }, [totalMonthlyBudget, getAllocatedBudget])

  return {
    categories,
    totalMonthlyBudget,
    maxCategories,
    loading,
    error,
    refetch: fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    reorderCategories,
    updateTotalBudget,
    getAllocatedBudget,
    getAvailableBudget,
  }
}

export default useCategories
