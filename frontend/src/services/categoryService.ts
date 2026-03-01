import api from './api'
import type {
  CategoryCreate,
  CategoryUpdate,
  CategoriesResponse,
  CategoryDefaults,
  TotalBudgetResponse,
} from '@/types/category'

export const categoryService = {
  /**
   * Get all categories for the current user
   */
  async getCategories(): Promise<CategoriesResponse> {
    const response = await api.get<CategoriesResponse>('/categories')
    return response.data
  },

  /**
   * Create a new category
   */
  async createCategory(data: CategoryCreate): Promise<{ success: boolean; category_id: string; message: string }> {
    const response = await api.post('/categories', data)
    return response.data
  },

  /**
   * Update a category
   */
  async updateCategory(
    categoryId: string,
    data: CategoryUpdate
  ): Promise<{ success: boolean; category_id: string; message: string }> {
    const response = await api.put(`/categories/${categoryId}`, data)
    return response.data
  },

  /**
   * Delete a category and reassign expenses
   */
  async deleteCategory(
    categoryId: string,
    reassignTo: string = 'OTHER'
  ): Promise<{ success: boolean; reassigned_count: number; message: string }> {
    const response = await api.delete(`/categories/${categoryId}`, {
      params: { reassign_to: reassignTo },
    })
    return response.data
  },

  /**
   * Reorder categories
   */
  async reorderCategories(categoryIds: string[]): Promise<{ success: boolean; message: string }> {
    const response = await api.put('/categories/reorder', { category_ids: categoryIds })
    return response.data
  },

  /**
   * Get default categories (for new users)
   */
  async getDefaultCategories(): Promise<CategoryDefaults> {
    const response = await api.get<CategoryDefaults>('/categories/defaults')
    return response.data
  },

  /**
   * Get total budget info
   */
  async getTotalBudget(): Promise<TotalBudgetResponse> {
    const response = await api.get<TotalBudgetResponse>('/budget/total')
    return response.data
  },

  /**
   * Update total monthly budget
   */
  async updateTotalBudget(
    totalMonthlyBudget: number
  ): Promise<{ success: boolean; total_monthly_budget: number; other_cap: number }> {
    const response = await api.put('/budget/total', { total_monthly_budget: totalMonthlyBudget })
    return response.data
  },

  /**
   * Complete onboarding by setting up budget and categories
   */
  async completeOnboarding(data: {
    total_budget: number
    selected_category_ids: string[]
    category_caps: Record<string, number>
    custom_categories?: Array<{
      display_name: string
      icon: string
      color: string
      monthly_cap: number
    }>
    excluded_category_ids?: string[]
  }): Promise<{
    success: boolean
    total_budget: number
    categories_created: number
    other_cap: number
    message: string
  }> {
    const response = await api.post('/onboarding/complete', data)
    return response.data
  },
}

export default categoryService
