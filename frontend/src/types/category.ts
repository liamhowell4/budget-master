export interface Category {
  category_id: string
  display_name: string
  icon: string
  color: string
  monthly_cap: number
  is_system: boolean
  created_at?: string
  sort_order: number
  exclude_from_total: boolean  // If true, this category won't count toward overall budget total
}

export interface CategoryCreate {
  display_name: string
  icon: string
  color: string
  monthly_cap: number
}

export interface CategoryUpdate {
  display_name?: string
  icon?: string
  color?: string
  monthly_cap?: number
  sort_order?: number
  exclude_from_total?: boolean
}

export interface CategoriesResponse {
  categories: Category[]
  total_monthly_budget: number
  max_categories: number
}

export interface CategoryDefaults {
  defaults: DefaultCategory[]
  max_categories: number
}

export interface DefaultCategory {
  category_id: string
  display_name: string
  icon: string
  color: string
  description: string
  is_system: boolean
}

export interface TotalBudgetResponse {
  total_monthly_budget: number
  allocated: number
  available: number
}
