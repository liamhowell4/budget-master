import { useState } from 'react'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { CATEGORY_COLORS, CATEGORY_LABELS } from '@/utils/constants'
import { CategoryExpensesModal } from '@/components/ui/CategoryExpensesModal'
import { useCategories } from '@/hooks/useCategories'
import { formatToolDate, formatDateRange } from './cardUtils'
import type { ToolDate } from './cardUtils'
import type { ExpenseType } from '@/types/expense'
import type { BudgetCategory } from '@/types/budget'

interface LargestExpense {
  name: string
  amount: number
  date: ToolDate
  category: string
}

interface LargestExpensesResult {
  largest_expenses: LargestExpense[]
  start_date: ToolDate
  end_date: ToolDate
  category?: string
}

export function isLargestExpensesResult(result: unknown): result is LargestExpensesResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'largest_expenses' in result &&
    Array.isArray((result as LargestExpensesResult).largest_expenses)
  )
}

interface TopExpensesCardProps {
  result: LargestExpensesResult
}

export function TopExpensesCard({ result }: TopExpensesCardProps) {
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const { categories } = useCategories()

  const year = result.end_date.year
  const month = result.end_date.month

  const categoryFilter = result.category
    ? CATEGORY_LABELS[result.category as ExpenseType] ?? result.category
    : null

  const handleExpenseClick = (expense: LargestExpense) => {
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
          'border border-[var(--border-primary)]/50',
          'bg-[var(--surface-secondary)]'
        )}
      >
        <div className="mb-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-[var(--text-primary)]">
              Top Expenses
            </h3>
            {categoryFilter && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface-active)] text-[var(--text-secondary)]">
                {categoryFilter}
              </span>
            )}
          </div>
          <p className="text-xs text-[var(--text-muted)]">
            {formatDateRange(result.start_date, result.end_date)}
          </p>
        </div>

        <div className="space-y-2">
          {result.largest_expenses.map((expense, index) => {
            const category = expense.category as ExpenseType
            const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER
            const isTop = index === 0

            return (
              <button
                key={index}
                onClick={() => handleExpenseClick(expense)}
                className={cn(
                  'w-full flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left',
                  'hover:opacity-80 transition-opacity cursor-pointer',
                  isTop
                    ? 'bg-amber-50/80 dark:bg-amber-950/20'
                    : 'bg-[var(--surface-primary)]'
                )}
              >
                <span
                  className={cn(
                    'flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold',
                    isTop
                      ? 'bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200'
                      : 'bg-[var(--surface-active)] text-[var(--text-muted)]'
                  )}
                >
                  {index + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                    {expense.name}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn('w-2 h-2 rounded-full flex-shrink-0', colors.bg)}
                      style={{
                        backgroundColor:
                          colors.accent.includes('emerald')
                            ? '#059669'
                            : colors.accent.includes('amber')
                              ? '#d97706'
                              : colors.accent.includes('teal')
                                ? '#0d9488'
                                : undefined,
                      }}
                    />
                    <span className="text-xs text-[var(--text-muted)]">
                      {CATEGORY_LABELS[category] ?? expense.category}
                    </span>
                    {expense.date && (
                      <>
                        <span className="text-[var(--border-secondary)]">·</span>
                        <span className="text-xs text-[var(--text-muted)]">
                          {formatToolDate(expense.date)}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <span className="text-sm font-semibold text-[var(--text-primary)] tabular-nums flex-shrink-0">
                  {formatCurrency(expense.amount)}
                </span>
              </button>
            )
          })}
        </div>
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
