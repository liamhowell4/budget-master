import { useState } from 'react'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { CATEGORY_COLORS, CATEGORY_LABELS } from '@/utils/constants'
import { CategoryIcon } from '@/components/ui/CategoryIcon'
import { CategoryExpensesModal } from '@/components/ui/CategoryExpensesModal'
import { useCategories } from '@/hooks/useCategories'
import type { ExpenseType } from '@/types/expense'
import type { BudgetCategory } from '@/types/budget'

// --- Create mode types ---
interface CreateRecurringResult {
  success: boolean
  template_id: string
  expense_name: string
  amount: number
  category: string
  frequency: string
  message: string
}

export function isCreateRecurringResult(result: unknown): result is CreateRecurringResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'success' in result &&
    'template_id' in result &&
    'frequency' in result &&
    'expense_name' in result
  )
}

// --- List mode types ---
interface RecurringItem {
  template_id: string
  expense_name: string
  amount: number
  category: string
  frequency: string
  active: boolean
  schedule?: string
}

interface ListRecurringResult {
  count: number
  recurring_expenses: RecurringItem[]
}

export function isListRecurringResult(result: unknown): result is ListRecurringResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'recurring_expenses' in result &&
    Array.isArray((result as ListRecurringResult).recurring_expenses)
  )
}

// --- Frequency badge ---
const FREQUENCY_STYLES: Record<string, string> = {
  monthly: 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300',
  weekly: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
  biweekly: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300',
  yearly: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
}

function FrequencyBadge({ frequency }: { frequency: string }) {
  const label = frequency.charAt(0).toUpperCase() + frequency.slice(1)
  const style = FREQUENCY_STYLES[frequency] ?? 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'
  return (
    <span className={cn('text-xs px-1.5 py-0.5 rounded-full font-medium', style)}>
      {label}
    </span>
  )
}

// --- Main component ---
interface RecurringExpenseCardProps {
  mode: 'create' | 'list'
  createResult?: CreateRecurringResult
  listResult?: ListRecurringResult
}

export function RecurringExpenseCard({ mode, createResult, listResult }: RecurringExpenseCardProps) {
  if (mode === 'create' && createResult) {
    return <CreateCard result={createResult} />
  }
  if (mode === 'list' && listResult) {
    return <ListCard result={listResult} />
  }
  return null
}

function CreateCard({ result }: { result: CreateRecurringResult }) {
  const category = result.category as ExpenseType
  const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER
  const label = CATEGORY_LABELS[category] ?? result.category

  return (
    <div
      className={cn(
        'rounded-xl p-4 max-w-sm',
        'border border-neutral-200/50 dark:border-neutral-700/50',
        'transition-all duration-200',
        colors.bg
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={cn('flex items-center gap-1.5', colors.accent)}>
          <CategoryIcon category={category} className="h-4 w-4" />
          <span className="text-xs font-medium">{label}</span>
        </div>
        <FrequencyBadge frequency={result.frequency} />
      </div>

      <div className="flex items-baseline justify-between">
        <h3 className="text-base font-medium text-neutral-900 dark:text-neutral-100 truncate pr-2">
          {result.expense_name}
        </h3>
        <span className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
          {formatCurrency(result.amount)}
        </span>
      </div>
    </div>
  )
}

function ListCard({ result }: { result: ListRecurringResult }) {
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const { categories } = useCategories()

  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1

  const handleItemClick = (item: RecurringItem) => {
    setSelectedCategory({
      category: item.category,
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
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Recurring Expenses
          </h3>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
            {result.count} item{result.count !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="space-y-2">
          {result.recurring_expenses.map((item) => {
            const category = item.category as ExpenseType
            const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER

            return (
              <button
                key={item.template_id}
                onClick={() => handleItemClick(item)}
                className="w-full flex items-center gap-2 py-1.5 hover:opacity-80 transition-opacity cursor-pointer text-left"
              >
                <span className={cn('w-2 h-2 rounded-full flex-shrink-0', colors.bg)} />
                <span className="text-sm text-neutral-900 dark:text-neutral-100 truncate flex-1 min-w-0">
                  {item.expense_name}
                </span>
                <FrequencyBadge frequency={item.frequency} />
                <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100 tabular-nums flex-shrink-0">
                  {formatCurrency(item.amount)}
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
