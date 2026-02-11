import { useState, useMemo } from 'react'
import { ArrowUpDown, Calendar, TrendingDown, TrendingUp } from 'lucide-react'
import { Modal } from './Modal'
import { ProgressBar } from './ProgressBar'
import { Spinner } from './Spinner'
import { useExpenses } from '@/hooks/useExpenses'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import type { BudgetCategory } from '@/types/budget'
import type { Expense } from '@/types/expense'
import type { Category } from '@/types/category'

// Legacy fallback labels for backward compatibility
const LEGACY_CATEGORY_LABELS: Record<string, string> = {
  FOOD_OUT: 'Dining',
  COFFEE: 'Coffee',
  GROCERIES: 'Groceries',
  RENT: 'Rent',
  UTILITIES: 'Utilities',
  MEDICAL: 'Medical',
  GAS: 'Gas',
  RIDE_SHARE: 'Rides',
  HOTEL: 'Hotel',
  TECH: 'Tech',
  TRAVEL: 'Travel',
  OTHER: 'Other',
}

export function getCategoryDisplayName(categoryId: string, categories: Category[]): string {
  const category = categories.find((c) => c.category_id === categoryId)
  if (category) return category.display_name
  return LEGACY_CATEGORY_LABELS[categoryId] || categoryId
}

type SortOption = 'date-desc' | 'date-asc' | 'amount-desc' | 'amount-asc'

const SORT_OPTIONS: { value: SortOption; label: string; icon: typeof Calendar }[] = [
  { value: 'date-desc', label: 'Newest first', icon: Calendar },
  { value: 'date-asc', label: 'Oldest first', icon: Calendar },
  { value: 'amount-desc', label: 'Highest amount', icon: TrendingUp },
  { value: 'amount-asc', label: 'Lowest amount', icon: TrendingDown },
]

function sortExpenses(expenses: Expense[], sortBy: SortOption): Expense[] {
  return [...expenses].sort((a, b) => {
    switch (sortBy) {
      case 'date-desc':
        return (
          new Date(b.date.year, b.date.month - 1, b.date.day).getTime() -
          new Date(a.date.year, a.date.month - 1, a.date.day).getTime()
        )
      case 'date-asc':
        return (
          new Date(a.date.year, a.date.month - 1, a.date.day).getTime() -
          new Date(b.date.year, b.date.month - 1, b.date.day).getTime()
        )
      case 'amount-desc':
        return b.amount - a.amount
      case 'amount-asc':
        return a.amount - b.amount
      default:
        return 0
    }
  })
}

interface CategoryExpensesModalProps {
  category: BudgetCategory | null
  isOpen: boolean
  onClose: () => void
  categories: Category[]
  year: number
  month: number
}

export function CategoryExpensesModal({
  category,
  isOpen,
  onClose,
  categories,
  year,
  month,
}: CategoryExpensesModalProps) {
  const [sortBy, setSortBy] = useState<SortOption>('date-desc')
  const { expenses, loading } = useExpenses(
    year,
    month,
    category?.category
  )

  const sortedExpenses = useMemo(() => sortExpenses(expenses, sortBy), [expenses, sortBy])

  const stats = useMemo(() => {
    if (expenses.length === 0) return null
    const total = expenses.reduce((sum, e) => sum + e.amount, 0)
    return {
      total,
      count: expenses.length,
      average: total / expenses.length,
    }
  }, [expenses])

  if (!category) return null

  const displayName = getCategoryDisplayName(category.category, categories)
  const hasBudgetData = category.cap > 0

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${displayName} Expenses`}
      className="max-w-lg"
    >
      <div className="space-y-4">
        {/* Stats summary - only shown when budget data is available */}
        {hasBudgetData && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <p className="text-xs text-neutral-500 dark:text-neutral-400">Spent</p>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  {formatCurrency(category.spending)}
                </p>
              </div>
              <div className="text-center p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <p className="text-xs text-neutral-500 dark:text-neutral-400">Budget</p>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  {formatCurrency(category.cap)}
                </p>
              </div>
              <div className="text-center p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <p className="text-xs text-neutral-500 dark:text-neutral-400">Remaining</p>
                <p
                  className={cn(
                    'text-lg font-semibold',
                    category.remaining >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  )}
                >
                  {formatCurrency(category.remaining)}
                </p>
              </div>
            </div>

            {/* Progress bar */}
            <ProgressBar percentage={category.percentage} />
          </>
        )}

        {/* Sort dropdown */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            {stats ? `${stats.count} expense${stats.count !== 1 ? 's' : ''}` : 'No expenses'}
          </p>
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className={cn(
                'appearance-none pl-8 pr-3 py-1.5 rounded-md text-xs',
                'bg-neutral-100 dark:bg-neutral-800',
                'border border-neutral-200 dark:border-neutral-700',
                'text-neutral-700 dark:text-neutral-300',
                'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600',
                'cursor-pointer'
              )}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400 pointer-events-none" />
          </div>
        </div>

        {/* Expense list */}
        {loading ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : sortedExpenses.length === 0 ? (
          <div className="text-center py-8 text-sm text-neutral-500 dark:text-neutral-400">
            No expenses in this category
          </div>
        ) : (
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {sortedExpenses.map((expense) => (
              <div
                key={expense.id}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg',
                  'bg-neutral-50 dark:bg-neutral-800'
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                    {expense.expense_name}
                  </p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500">
                    {formatExpenseDate(expense.date)}
                  </p>
                </div>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 ml-3">
                  {formatCurrency(expense.amount)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Average spending */}
        {stats && stats.count > 1 && (
          <div className="pt-3 border-t border-neutral-200 dark:border-neutral-800">
            <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center">
              Average: {formatCurrency(stats.average)} per expense
            </p>
          </div>
        )}
      </div>
    </Modal>
  )
}
