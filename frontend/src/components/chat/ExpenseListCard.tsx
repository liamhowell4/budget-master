import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { CATEGORY_COLORS } from '@/utils/constants'
import { CategoryExpensesModal } from '@/components/ui/CategoryExpensesModal'
import { useCategories } from '@/hooks/useCategories'
import { formatToolDate } from './cardUtils'
import type { ToolDate } from './cardUtils'
import type { ExpenseType } from '@/types/expense'
import type { BudgetCategory } from '@/types/budget'

interface ExpenseItem {
  id?: string
  name?: string
  expense_name?: string
  amount: number
  category: string
  date?: ToolDate
}

interface ExpenseListResult {
  expenses: ExpenseItem[]
  count: number
  total?: number
  query?: string
  start_date?: ToolDate
  end_date?: ToolDate
}

export function isExpenseListResult(result: unknown): result is ExpenseListResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'expenses' in result &&
    Array.isArray((result as ExpenseListResult).expenses) &&
    'count' in result
  )
}

interface ExpenseListCardProps {
  result: ExpenseListResult
  toolName: string
}

const INITIAL_SHOW = 5

export function ExpenseListCard({ result, toolName }: ExpenseListCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const { categories } = useCategories()

  // Determine year/month for modal from result dates or current date
  const now = new Date()
  const year = result.end_date?.year ?? now.getFullYear()
  const month = result.end_date?.month ?? (now.getMonth() + 1)

  const title =
    toolName === 'search_expenses' && result.query
      ? `Results for "${result.query}"`
      : toolName === 'get_recent_expenses'
        ? 'Recent Expenses'
        : 'Expenses'

  const expenses = result.expenses
  const visibleExpenses = expanded ? expenses : expenses.slice(0, INITIAL_SHOW)
  const hiddenCount = expenses.length - INITIAL_SHOW

  const handleExpenseClick = (expense: ExpenseItem) => {
    setSelectedCategory({
      category: expense.category,
      spending: 0,
      cap: 0,
      percentage: 0,
      remaining: 0,
    })
  }

  return (
    <>
      <div
        className={cn(
          'rounded-xl p-4 max-w-sm',
          'border border-neutral-200/50 dark:border-neutral-700/50',
          'bg-neutral-50 dark:bg-neutral-800/60'
        )}
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{title}</h3>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
            {result.count} item{result.count !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="space-y-1">
          {visibleExpenses.map((expense, index) => {
            const name = expense.name ?? expense.expense_name ?? 'Unknown'
            const category = expense.category as ExpenseType
            const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER

            return (
              <button
                key={expense.id ?? index}
                onClick={() => handleExpenseClick(expense)}
                className="w-full flex items-center gap-2 py-1.5 hover:opacity-80 transition-opacity cursor-pointer text-left"
              >
                <span className={cn('w-2 h-2 rounded-full flex-shrink-0', colors.bg)} />
                <span className="text-sm text-neutral-900 dark:text-neutral-100 truncate flex-1 min-w-0">
                  {name}
                </span>
                {expense.date && (
                  <span className="text-xs text-neutral-400 dark:text-neutral-500 flex-shrink-0">
                    {formatToolDate(expense.date)}
                  </span>
                )}
                <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100 tabular-nums flex-shrink-0">
                  {formatCurrency(expense.amount)}
                </span>
              </button>
            )
          })}
        </div>

        {/* Show more toggle */}
        {hiddenCount > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className={cn(
              'flex items-center gap-1 mt-2 text-xs font-medium',
              'text-neutral-500 dark:text-neutral-400',
              'hover:text-neutral-700 dark:hover:text-neutral-300',
              'transition-colors'
            )}
          >
            <ChevronDown
              className={cn('h-3.5 w-3.5 transition-transform', expanded && 'rotate-180')}
            />
            {expanded ? 'Show less' : `Show ${hiddenCount} more`}
          </button>
        )}

        {/* Total row */}
        {result.total != null && (
          <div className="mt-2 pt-2 border-t border-neutral-200/50 dark:border-neutral-700/50 flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Total</span>
            <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
              {formatCurrency(result.total)}
            </span>
          </div>
        )}
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
