import { useState, useMemo } from 'react'
import { Card, ProgressBar, Spinner, CategoryIcon, Modal } from '@/components/ui'
import { useBudget, invalidateBudgetCache } from '@/hooks/useBudget'
import { useExpenses } from '@/hooks/useExpenses'
import { updateBudgetCaps } from '@/services/budgetService'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import { ArrowUpDown, Calendar, TrendingDown, TrendingUp, Pencil } from 'lucide-react'
import type { BudgetCategory, BudgetStatus } from '@/types/budget'
import type { Expense, ExpenseType } from '@/types/expense'

const CATEGORY_LABELS: Record<string, string> = {
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

const ALL_CATEGORIES: ExpenseType[] = [
  'FOOD_OUT',
  'COFFEE',
  'GROCERIES',
  'RENT',
  'UTILITIES',
  'MEDICAL',
  'GAS',
  'RIDE_SHARE',
  'HOTEL',
  'TECH',
  'TRAVEL',
  'OTHER',
]

function EditBudgetModal({
  isOpen,
  onClose,
  budget,
  onSaved,
}: {
  isOpen: boolean
  onClose: () => void
  budget: BudgetStatus
  onSaved: () => void
}) {
  const [totalBudget, setTotalBudget] = useState(budget.total_cap.toString())
  const [categoryBudgets, setCategoryBudgets] = useState<Record<string, string>>(() => {
    const caps: Record<string, string> = {}
    for (const cat of ALL_CATEGORIES) {
      const existing = budget.categories.find((c) => c.category === cat)
      caps[cat] = existing ? existing.cap.toString() : '0'
    }
    return caps
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCategoryChange = (category: string, value: string) => {
    setCategoryBudgets((prev) => ({ ...prev, [category]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)

    try {
      const total = parseFloat(totalBudget) || 0
      const cats: Record<string, number> = {}
      for (const [cat, val] of Object.entries(categoryBudgets)) {
        cats[cat] = parseFloat(val) || 0
      }

      await updateBudgetCaps(total, cats)
      invalidateBudgetCache()
      onSaved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save budget')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Budget" className="max-w-md">
      <div className="space-y-5">
        {error && (
          <div className="p-3 rounded-md bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
            Total Monthly Budget
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">$</span>
            <input
              type="number"
              value={totalBudget}
              onChange={(e) => setTotalBudget(e.target.value)}
              className={cn(
                'w-full pl-7 pr-3 py-2 rounded-md',
                'bg-neutral-50 dark:bg-neutral-800',
                'border border-neutral-200 dark:border-neutral-700',
                'text-neutral-900 dark:text-neutral-100',
                'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-500'
              )}
              min="0"
              step="0.01"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
            Category Budgets
          </label>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {ALL_CATEGORIES.map((cat) => (
              <div key={cat} className="flex items-center gap-3">
                <div className="flex items-center gap-2 w-28">
                  <CategoryIcon
                    category={cat}
                    className="h-4 w-4 text-neutral-400 dark:text-neutral-500"
                  />
                  <span className="text-sm text-neutral-600 dark:text-neutral-400">
                    {CATEGORY_LABELS[cat]}
                  </span>
                </div>
                <div className="relative flex-1">
                  <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">
                    $
                  </span>
                  <input
                    type="number"
                    value={categoryBudgets[cat]}
                    onChange={(e) => handleCategoryChange(cat, e.target.value)}
                    className={cn(
                      'w-full pl-6 pr-2 py-1.5 rounded-md text-sm',
                      'bg-neutral-50 dark:bg-neutral-800',
                      'border border-neutral-200 dark:border-neutral-700',
                      'text-neutral-900 dark:text-neutral-100',
                      'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-500'
                    )}
                    min="0"
                    step="0.01"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={onClose}
            disabled={saving}
            className={cn(
              'flex-1 px-4 py-2 rounded-md text-sm font-medium',
              'bg-neutral-100 dark:bg-neutral-800',
              'text-neutral-700 dark:text-neutral-300',
              'hover:bg-neutral-200 dark:hover:bg-neutral-700',
              'transition-colors',
              'disabled:opacity-50'
            )}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={cn(
              'flex-1 px-4 py-2 rounded-md text-sm font-medium',
              'bg-neutral-900 dark:bg-neutral-100',
              'text-white dark:text-neutral-900',
              'hover:opacity-90 transition-opacity',
              'disabled:opacity-50'
            )}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </Modal>
  )
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

function CategoryExpensesModal({
  category,
  isOpen,
  onClose,
}: {
  category: BudgetCategory | null
  isOpen: boolean
  onClose: () => void
}) {
  const [sortBy, setSortBy] = useState<SortOption>('date-desc')
  const now = new Date()
  const { expenses, loading } = useExpenses(
    now.getFullYear(),
    now.getMonth() + 1,
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${CATEGORY_LABELS[category.category] || category.category} Expenses`}
      className="max-w-lg"
    >
      <div className="space-y-4">
        {/* Stats summary */}
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

export function DashboardPage() {
  const { budget, loading, error, refetch } = useBudget()
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)

  if (loading) {
    return (
      <div className="flex h-[calc(100dvh-56px)] items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-[calc(100dvh-56px)] flex-col items-center justify-center gap-4 p-6">
        <p className="text-sm text-red-500">{error}</p>
        <button
          onClick={refetch}
          className={cn(
            'px-4 py-2 rounded-md text-sm font-medium',
            'bg-neutral-900 dark:bg-neutral-100',
            'text-white dark:text-neutral-900',
            'hover:opacity-90 transition-opacity'
          )}
        >
          Try again
        </button>
      </div>
    )
  }

  if (!budget) return null

  const activeCategories = budget.categories.filter((cat) => cat.cap > 0)

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 sm:p-6 space-y-6 sm:space-y-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
              Dashboard
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
              {budget.month_name} budget overview
            </p>
          </div>
          <button
            onClick={() => setShowEditModal(true)}
            className={cn(
              'p-2 rounded-md',
              'text-neutral-500 dark:text-neutral-400',
              'hover:bg-neutral-100 dark:hover:bg-neutral-800',
              'hover:text-neutral-700 dark:hover:text-neutral-200',
              'transition-colors'
            )}
            aria-label="Edit budget"
          >
            <Pencil className="h-4 w-4" />
          </button>
        </div>

        <Card padding="lg">
          <div className="space-y-4">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-1">
                  Remaining
                </p>
                <span className="text-3xl font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight">
                  {formatCurrency(budget.total_remaining)}
                </span>
              </div>
              <span className="text-sm text-neutral-500 dark:text-neutral-400">
                {budget.total_percentage.toFixed(0)}% used
              </span>
            </div>
            <ProgressBar percentage={budget.total_percentage} />
            <div className="flex justify-between text-sm text-neutral-400 dark:text-neutral-500">
              <span>Spent: {formatCurrency(budget.total_spending)}</span>
              <span>Budget: {formatCurrency(budget.total_cap)}</span>
            </div>
          </div>
        </Card>

        {activeCategories.length > 0 && (
          <div>
            <h2 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-4">
              Categories
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {activeCategories.map((cat) => (
                <button
                  key={cat.category}
                  onClick={() => setSelectedCategory(cat)}
                  className="text-left w-full"
                >
                  <Card padding="md" hover>
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-100 dark:bg-neutral-800">
                        <CategoryIcon
                          category={cat.category}
                          className="h-5 w-5 text-neutral-500 dark:text-neutral-400"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                            {CATEGORY_LABELS[cat.category] || cat.category}
                          </span>
                          <span className="text-xs text-neutral-500 dark:text-neutral-400">
                            {formatCurrency(cat.spending)} / {formatCurrency(cat.cap)}
                          </span>
                        </div>
                        <ProgressBar percentage={cat.percentage} size="sm" />
                      </div>
                    </div>
                  </Card>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeCategories.length === 0 && (
          <Card padding="lg">
            <p className="text-center text-sm text-neutral-500 dark:text-neutral-400">
              No budget caps configured yet. Start tracking expenses to see category breakdowns.
            </p>
          </Card>
        )}

        {/* Category Expenses Modal */}
        <CategoryExpensesModal
          category={selectedCategory}
          isOpen={selectedCategory !== null}
          onClose={() => setSelectedCategory(null)}
        />

        {/* Edit Budget Modal */}
        {budget && (
          <EditBudgetModal
            isOpen={showEditModal}
            onClose={() => setShowEditModal(false)}
            budget={budget}
            onSaved={refetch}
          />
        )}
    </div>
  )
}
