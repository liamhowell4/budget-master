import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { CATEGORY_LABELS, CATEGORY_COLORS } from '@/utils/constants'
import { CategoryIcon } from '@/components/ui/CategoryIcon'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { CategoryExpensesModal } from '@/components/ui/CategoryExpensesModal'
import { useCategories } from '@/hooks/useCategories'
import type { ExpenseType } from '@/types/expense'
import type { BudgetCategory } from '@/types/budget'

interface BudgetCategoryItem {
  category: string
  spending: number
  cap: number
  percentage: number
  remaining: number
}

// All-categories response shape
interface BudgetRemainingAllResult {
  categories: BudgetCategoryItem[]
  total: {
    spending: number
    cap: number
    percentage: number
    remaining: number
  }
}

// Single-category response shape
interface BudgetRemainingSingleResult {
  category: string
  spending: number
  cap: number
  percentage: number
  remaining: number
}

type BudgetRemainingResult = BudgetRemainingAllResult | BudgetRemainingSingleResult

function isAllCategoriesResult(result: BudgetRemainingResult): result is BudgetRemainingAllResult {
  return 'categories' in result && Array.isArray(result.categories)
}

export function isBudgetRemainingResult(result: unknown): result is BudgetRemainingResult {
  if (typeof result !== 'object' || result === null) return false
  if ('categories' in result && 'total' in result) return true
  if ('category' in result && 'spending' in result && 'cap' in result && 'percentage' in result) return true
  return false
}

interface BudgetRemainingCardProps {
  result: BudgetRemainingResult
}

export function BudgetRemainingCard({ result }: BudgetRemainingCardProps) {
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const { categories } = useCategories()
  const navigate = useNavigate()

  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1

  // Single-category view
  if (!isAllCategoriesResult(result)) {
    const category = result.category as ExpenseType
    const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER
    const label = CATEGORY_LABELS[category] ?? result.category

    const budgetCat: BudgetCategory = {
      category: result.category,
      spending: result.spending,
      cap: result.cap,
      percentage: result.percentage,
      remaining: result.remaining,
    }

    return (
      <>
        <button
          onClick={() => setSelectedCategory(budgetCat)}
          className="text-left w-full"
        >
          <div
            className={cn(
              'rounded-xl p-4 max-w-sm',
              'border border-neutral-200/50 dark:border-neutral-700/50',
              'bg-neutral-50 dark:bg-neutral-800/60',
              'hover:border-neutral-300 dark:hover:border-neutral-600 transition-colors cursor-pointer'
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Budget Status
              </h3>
              <div className={cn('flex items-center gap-1.5', colors.accent)}>
                <CategoryIcon category={category} className="h-3.5 w-3.5" />
                <span className="text-xs font-medium">{label}</span>
              </div>
            </div>

            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
                {formatCurrency(result.spending)} / {formatCurrency(result.cap)}
              </span>
              <span className="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
                {result.percentage.toFixed(0)}%
              </span>
            </div>
            <ProgressBar percentage={result.percentage} size="sm" />
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5 tabular-nums">
              {formatCurrency(result.remaining)} remaining
            </p>
          </div>
        </button>

        <CategoryExpensesModal
          category={selectedCategory}
          isOpen={selectedCategory !== null}
          onClose={() => setSelectedCategory(null)}
          categories={categories}
          year={year}
          month={month}
        />
      </>
    )
  }

  // All-categories view
  return (
    <>
      <div
        className={cn(
          'rounded-xl p-4 max-w-sm',
          'border border-neutral-200/50 dark:border-neutral-700/50',
          'bg-neutral-50 dark:bg-neutral-800/60'
        )}
      >
        <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-3">
          Budget Status
        </h3>

        <div className="space-y-2.5">
          {result.categories.map((cat) => {
            const category = cat.category as ExpenseType
            const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER
            const label = CATEGORY_LABELS[category] ?? cat.category

            return (
              <button
                key={cat.category}
                onClick={() => setSelectedCategory({
                  category: cat.category,
                  spending: cat.spending,
                  cap: cat.cap,
                  percentage: cat.percentage,
                  remaining: cat.remaining,
                })}
                className="w-full text-left hover:opacity-80 transition-opacity cursor-pointer"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className={cn('flex items-center gap-1.5', colors.accent)}>
                    <CategoryIcon category={category} className="h-3.5 w-3.5" />
                    <span className="text-xs font-medium">{label}</span>
                  </div>
                  <span className="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
                    {formatCurrency(cat.spending)} / {formatCurrency(cat.cap)}
                  </span>
                </div>
                <ProgressBar percentage={cat.percentage} size="sm" />
              </button>
            )
          })}
        </div>

        {/* Total section - navigates to /dashboard */}
        <button
          onClick={() => navigate('/dashboard')}
          className="w-full text-left mt-3 pt-3 border-t border-neutral-200/50 dark:border-neutral-700/50 hover:opacity-80 transition-opacity cursor-pointer"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-neutral-900 dark:text-neutral-100">
              Total
            </span>
            <span className="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
              {formatCurrency(result.total.spending)} / {formatCurrency(result.total.cap)}
            </span>
          </div>
          <ProgressBar percentage={result.total.percentage} size="sm" />
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 tabular-nums">
            {formatCurrency(result.total.remaining)} remaining
          </p>
        </button>
      </div>

      <CategoryExpensesModal
        category={selectedCategory}
        isOpen={selectedCategory !== null}
        onClose={() => setSelectedCategory(null)}
        categories={categories}
        year={year}
        month={month}
      />
    </>
  )
}
