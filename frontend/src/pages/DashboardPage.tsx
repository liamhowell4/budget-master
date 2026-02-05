import { useState, useMemo } from 'react'
import { Card, ProgressBar, Spinner, CategoryIcon, Modal, DynamicIcon } from '@/components/ui'
import { useBudget } from '@/hooks/useBudget'
import { useExpenses } from '@/hooks/useExpenses'
import { useCategories } from '@/hooks/useCategories'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import { ArrowUpDown, Calendar, TrendingDown, TrendingUp, Settings, EyeOff, ChevronLeft, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { BudgetCategory } from '@/types/budget'
import type { Expense } from '@/types/expense'
import type { Category } from '@/types/category'

// Check if a given year/month is the current month
function isCurrentMonth(year: number, month: number): boolean {
  const now = new Date()
  return year === now.getFullYear() && month === now.getMonth() + 1
}

// Helper to get days in a month
function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

// Helper to calculate pace (% used / % of month elapsed)
function calculatePace(percentage: number, year: number, month: number): number {
  const now = new Date()
  const currentDay = now.getDate()
  const daysInMonth = getDaysInMonth(year, month)
  const monthProgress = (currentDay / daysInMonth) * 100

  if (monthProgress === 0) return 0
  return percentage / monthProgress
}

// Format pace for display
function formatPace(pace: number): string {
  return `${pace.toFixed(2)}x pace`
}

// Calculate dollar difference from 1x pace
// Negative = under pace (good), Positive = over pace (bad)
function calculatePaceDifference(spending: number, cap: number, year: number, month: number): number {
  const now = new Date()
  const currentDay = now.getDate()
  const daysInMonth = getDaysInMonth(year, month)
  const monthProgress = currentDay / daysInMonth
  const expectedSpending = cap * monthProgress
  return spending - expectedSpending
}

// Format pace difference for display
function formatPaceDifference(diff: number): string {
  const absDiff = Math.abs(diff)
  if (diff <= 0) {
    return `${formatCurrency(absDiff)} under`
  }
  return `${formatCurrency(absDiff)} over`
}

// Get pace status color class
function getPaceColorClass(pace: number): string {
  if (pace > 1.1) return 'text-red-600 dark:text-red-400'
  if (pace > 0.9) return 'text-amber-600 dark:text-amber-400'
  return 'text-emerald-600 dark:text-emerald-400'
}

// Get color class for pace difference
function getPaceDiffColorClass(diff: number): string {
  if (diff > 0) return 'text-red-600 dark:text-red-400'
  if (diff < 0) return 'text-emerald-600 dark:text-emerald-400'
  return 'text-neutral-500 dark:text-neutral-400'
}

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

// Helper to get category display name
function getCategoryDisplayName(categoryId: string, categories: Category[]): string {
  const category = categories.find((c) => c.category_id === categoryId)
  if (category) return category.display_name
  return LEGACY_CATEGORY_LABELS[categoryId] || categoryId
}

// Helper to get category info
function getCategoryInfo(categoryId: string, categories: Category[]): Category | undefined {
  return categories.find((c) => c.category_id === categoryId)
}

// EditBudgetModal removed - budget editing now handled in Settings > Categories

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
  categories,
  year,
  month,
}: {
  category: BudgetCategory | null
  isOpen: boolean
  onClose: () => void
  categories: Category[]
  year: number
  month: number
}) {
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${displayName} Expenses`}
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
  const now = new Date()
  const [selectedYear, setSelectedYear] = useState(now.getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1)

  const { budget, loading, error, refetch } = useBudget(selectedYear, selectedMonth)
  const { categories, loading: categoriesLoading } = useCategories()
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const navigate = useNavigate()

  const isCurrentMonthSelected = isCurrentMonth(selectedYear, selectedMonth)

  const goToPreviousMonth = () => {
    if (selectedMonth === 1) {
      setSelectedYear(selectedYear - 1)
      setSelectedMonth(12)
    } else {
      setSelectedMonth(selectedMonth - 1)
    }
  }

  const goToNextMonth = () => {
    // Don't allow going beyond current month
    if (isCurrentMonthSelected) return

    if (selectedMonth === 12) {
      setSelectedYear(selectedYear + 1)
      setSelectedMonth(1)
    } else {
      setSelectedMonth(selectedMonth + 1)
    }
  }

  const goToCurrentMonth = () => {
    setSelectedYear(now.getFullYear())
    setSelectedMonth(now.getMonth() + 1)
  }

  if (loading || categoriesLoading) {
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

  // Filter active categories and sort by sort_order from categories list
  const activeCategories = budget.categories
    .filter((cat) => cat.cap > 0)
    .sort((a, b) => {
      const aOrder = categories.find((c) => c.category_id === a.category)?.sort_order ?? 999
      const bOrder = categories.find((c) => c.category_id === b.category)?.sort_order ?? 999
      return aOrder - bOrder
    })

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 sm:p-6 space-y-6 sm:space-y-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
              Dashboard
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <button
                onClick={goToPreviousMonth}
                className={cn(
                  'p-1 rounded-md',
                  'text-neutral-500 dark:text-neutral-400',
                  'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                  'hover:text-neutral-700 dark:hover:text-neutral-200',
                  'transition-colors'
                )}
                aria-label="Previous month"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={goToCurrentMonth}
                className={cn(
                  'text-sm font-medium min-w-[120px] text-center',
                  isCurrentMonthSelected
                    ? 'text-neutral-900 dark:text-neutral-100'
                    : 'text-blue-600 dark:text-blue-400 hover:underline'
                )}
                disabled={isCurrentMonthSelected}
              >
                {budget.month_name}
              </button>
              <button
                onClick={goToNextMonth}
                disabled={isCurrentMonthSelected}
                className={cn(
                  'p-1 rounded-md',
                  'transition-colors',
                  isCurrentMonthSelected
                    ? 'text-neutral-300 dark:text-neutral-600 cursor-not-allowed'
                    : 'text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-200'
                )}
                aria-label="Next month"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
          <button
            onClick={() => navigate('/settings')}
            className={cn(
              'p-2 rounded-md',
              'text-neutral-500 dark:text-neutral-400',
              'hover:bg-neutral-100 dark:hover:bg-neutral-800',
              'hover:text-neutral-700 dark:hover:text-neutral-200',
              'transition-colors'
            )}
            aria-label="Edit budget"
          >
            <Settings className="h-4 w-4" />
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
              <div className="text-right">
                <span className="text-sm text-neutral-500 dark:text-neutral-400 block">
                  {budget.total_percentage.toFixed(0)}% used
                </span>
                {isCurrentMonthSelected && (
                  <div className="text-xs">
                    <span className={getPaceColorClass(calculatePace(budget.total_percentage, budget.year, budget.month))}>
                      {formatPace(calculatePace(budget.total_percentage, budget.year, budget.month))}
                    </span>
                    <span className="text-neutral-300 dark:text-neutral-600 mx-1">|</span>
                    <span className={getPaceDiffColorClass(calculatePaceDifference(budget.total_spending, budget.total_cap, budget.year, budget.month))}>
                      {formatPaceDifference(calculatePaceDifference(budget.total_spending, budget.total_cap, budget.year, budget.month))}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <ProgressBar percentage={budget.total_percentage} />
            <div className="flex justify-between text-sm text-neutral-400 dark:text-neutral-500">
              <span>Spent: {formatCurrency(budget.total_spending)}</span>
              <span>Budget: {formatCurrency(budget.total_cap)}</span>
            </div>
            {isCurrentMonthSelected && (
              <div className="text-xs text-neutral-400 dark:text-neutral-500 text-center pt-2 border-t border-neutral-100 dark:border-neutral-800">
                Day {new Date().getDate()} of {getDaysInMonth(budget.year, budget.month)} ({((new Date().getDate() / getDaysInMonth(budget.year, budget.month)) * 100).toFixed(0)}% through month)
              </div>
            )}
            {budget.excluded_categories && budget.excluded_categories.length > 0 && (
              <div
                className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 pt-1 border-t border-neutral-100 dark:border-neutral-800 cursor-help relative group"
                title={budget.excluded_categories.map(catId => getCategoryDisplayName(catId, categories)).join(', ')}
              >
                <EyeOff className="h-3 w-3" />
                <span>
                  {budget.excluded_categories.length} {budget.excluded_categories.length === 1 ? 'category' : 'categories'} excluded from total
                </span>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-neutral-800 dark:bg-neutral-700 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                  {budget.excluded_categories.map(catId => getCategoryDisplayName(catId, categories)).join(', ')}
                </div>
              </div>
            )}
          </div>
        </Card>

        {activeCategories.length > 0 && (
          <div>
            <h2 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-4">
              Top Categories
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {activeCategories.map((cat) => {
                const categoryInfo = getCategoryInfo(cat.category, categories)
                const displayName = getCategoryDisplayName(cat.category, categories)
                const isExcluded = budget.excluded_categories?.includes(cat.category)

                return (
                  <button
                    key={cat.category}
                    onClick={() => setSelectedCategory(cat)}
                    className="text-left w-full"
                  >
                    <Card padding="md" hover>
                      <div className="flex items-center gap-3">
                        <div
                          className="flex h-10 w-10 items-center justify-center rounded-md"
                          style={{
                            backgroundColor: categoryInfo
                              ? `${categoryInfo.color}20`
                              : undefined,
                          }}
                        >
                          {categoryInfo ? (
                            <DynamicIcon
                              name={categoryInfo.icon}
                              className="h-5 w-5"
                              style={{ color: categoryInfo.color }}
                            />
                          ) : (
                            <CategoryIcon
                              category={cat.category}
                              className="h-5 w-5 text-neutral-500 dark:text-neutral-400"
                            />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                                {displayName}
                              </span>
                              {isExcluded && (
                                <span title="Not included in total">
                                  <EyeOff className="h-3.5 w-3.5 text-amber-500" />
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-neutral-500 dark:text-neutral-400">
                              {formatCurrency(cat.spending)} / {formatCurrency(cat.cap)}
                            </span>
                          </div>
                          <ProgressBar percentage={cat.percentage} size="sm" />
                        </div>
                      </div>
                    </Card>
                  </button>
                )
              })}
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
          categories={categories}
          year={selectedYear}
          month={selectedMonth}
        />
    </div>
  )
}
