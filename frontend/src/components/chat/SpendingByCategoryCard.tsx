import { useState } from 'react'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { CATEGORY_COLORS, CATEGORY_LABELS } from '@/utils/constants'
import { CategoryExpensesModal } from '@/components/ui/CategoryExpensesModal'
import { useCategories } from '@/hooks/useCategories'
import { formatDateRange } from './cardUtils'
import type { ToolDate } from './cardUtils'
import type { ExpenseType } from '@/types/expense'
import type { BudgetCategory } from '@/types/budget'

interface CategoryTransaction {
  name: string
  amount: number
  date?: ToolDate
}

interface CategoryBreakdown {
  category: string
  total: number
  count: number
  transactions: CategoryTransaction[]
}

interface SpendingByCategoryResult {
  breakdown: CategoryBreakdown[]
  total: number
  start_date: ToolDate
  end_date: ToolDate
}

export function isSpendingByCategoryResult(result: unknown): result is SpendingByCategoryResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'breakdown' in result &&
    Array.isArray((result as SpendingByCategoryResult).breakdown) &&
    'total' in result &&
    'start_date' in result &&
    'end_date' in result
  )
}

interface SpendingByCategoryCardProps {
  result: SpendingByCategoryResult
}

function CategoryRow({
  item,
  maxTotal,
  onClick,
}: {
  item: CategoryBreakdown
  maxTotal: number
  onClick: () => void
}) {
  const category = item.category as ExpenseType
  const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER
  const label = CATEGORY_LABELS[category] ?? item.category
  const barWidth = maxTotal > 0 ? (item.total / maxTotal) * 100 : 0

  const barColor = colors.accent.includes('emerald')
    ? 'bg-emerald-500 dark:bg-emerald-400'
    : colors.accent.includes('amber')
      ? 'bg-amber-500 dark:bg-amber-400'
      : colors.accent.includes('teal')
        ? 'bg-teal-500 dark:bg-teal-400'
        : colors.accent.includes('slate')
          ? 'bg-slate-500 dark:bg-slate-400'
          : colors.accent.includes('sky')
            ? 'bg-sky-500 dark:bg-sky-400'
            : colors.accent.includes('rose')
              ? 'bg-rose-500 dark:bg-rose-400'
              : colors.accent.includes('orange')
                ? 'bg-orange-500 dark:bg-orange-400'
                : colors.accent.includes('violet')
                  ? 'bg-violet-500 dark:bg-violet-400'
                  : colors.accent.includes('indigo')
                    ? 'bg-indigo-500 dark:bg-indigo-400'
                    : colors.accent.includes('cyan')
                      ? 'bg-cyan-500 dark:bg-cyan-400'
                      : colors.accent.includes('blue')
                        ? 'bg-blue-500 dark:bg-blue-400'
                        : 'bg-neutral-500 dark:bg-neutral-400'

  return (
    <button
      onClick={onClick}
      className="w-full text-left hover:opacity-80 transition-opacity cursor-pointer"
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          <span className={cn('text-xs font-medium', colors.accent)}>{label}</span>
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            ({item.count})
          </span>
        </div>
        <span className="text-xs font-medium text-neutral-900 dark:text-neutral-100 tabular-nums">
          {formatCurrency(item.total)}
        </span>
      </div>
      <div className="w-full h-2 rounded-full bg-neutral-200/60 dark:bg-neutral-700/40 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-300', barColor)}
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </button>
  )
}

export function SpendingByCategoryCard({ result }: SpendingByCategoryCardProps) {
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const { categories } = useCategories()
  const maxTotal = Math.max(...result.breakdown.map((b) => b.total), 0)

  const year = result.end_date.year
  const month = result.end_date.month

  const handleCategoryClick = (item: CategoryBreakdown) => {
    setSelectedCategory({
      category: item.category,
      spending: item.total,
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
        <div className="mb-3">
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Spending by Category
          </h3>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            {formatDateRange(result.start_date, result.end_date)}
          </p>
        </div>

        <div className="space-y-3">
          {result.breakdown.map((item) => (
            <CategoryRow
              key={item.category}
              item={item}
              maxTotal={maxTotal}
              onClick={() => handleCategoryClick(item)}
            />
          ))}
        </div>

        <div className="mt-3 pt-2 border-t border-neutral-200/50 dark:border-neutral-700/50 flex items-center justify-between">
          <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Total</span>
          <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
            {formatCurrency(result.total)}
          </span>
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
