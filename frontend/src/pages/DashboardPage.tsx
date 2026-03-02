import { useState } from 'react'
import { Card, ProgressBar, Spinner, CategoryIcon, DynamicIcon, CategoryExpensesModal, getCategoryDisplayName } from '@/components/ui'
import { useBudget, invalidateBudgetCache } from '@/hooks/useBudget'
import { useCategories } from '@/hooks/useCategories'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { Settings, EyeOff, ChevronLeft, ChevronRight, Calculator, Tag } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { BudgetCategory } from '@/types/budget'
import type { Category } from '@/types/category'
import { BudgetCalculatorModal } from '@/components/modals/BudgetCalculatorModal'
import { TipsWidget } from '@/components/dashboard/TipsWidget'
import { updateBudgetCaps } from '@/services/budgetService'

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
  if (pace > 1.1) return 'text-[var(--error)]'
  if (pace > 0.9) return 'text-[var(--warning)]'
  return 'text-[var(--success)]'
}

// Get color class for pace difference
function getPaceDiffColorClass(diff: number): string {
  if (diff > 0) return 'text-[var(--error)]'
  if (diff < 0) return 'text-[var(--success)]'
  return 'text-[var(--text-muted)]'
}

// Helper to get category info
function getCategoryInfo(categoryId: string, categories: Category[]): Category | undefined {
  return categories.find((c) => c.category_id === categoryId)
}

export function DashboardPage() {
  const now = new Date()
  const [selectedYear, setSelectedYear] = useState(now.getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1)

  const { budget, loading, error, refetch } = useBudget(selectedYear, selectedMonth)
  const { categories, loading: categoriesLoading } = useCategories()
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)
  const [calculatorOpen, setCalculatorOpen] = useState(false)
  const [showAllCategories, setShowAllCategories] = useState(false)
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

  const handleCalculatorApply = async (monthlyBudget: number) => {
    try {
      // Build current category budgets to preserve allocations
      const categoryBudgets: Record<string, number> = {}
      for (const cat of categories) {
        categoryBudgets[cat.category_id] = cat.monthly_cap
      }
      await updateBudgetCaps(monthlyBudget, categoryBudgets)
      invalidateBudgetCache()
      await refetch()
    } catch (err) {
      console.error('Failed to apply budget from calculator:', err)
    }
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
        <p className="text-sm text-[var(--error)]">{error}</p>
        <button
          onClick={refetch}
          className={cn(
            'px-4 py-2 rounded-md text-sm font-medium',
            'bg-[var(--text-primary)]',
            'text-[var(--text-inverted)]',
            'hover:opacity-90 transition-opacity'
          )}
        >
          Try again
        </button>
      </div>
    )
  }

  if (!budget) return null

  // All categories with a budget cap, sorted by sort_order
  const baseCategories = budget.categories
    .filter((cat) => cat.cap > 0)
    .sort((a, b) => {
      const aOrder = categories.find((c) => c.category_id === a.category)?.sort_order ?? 999
      const bOrder = categories.find((c) => c.category_id === b.category)?.sort_order ?? 999
      return aOrder - bOrder
    })

  // Show only categories with spending, unless showAllCategories is toggled
  const displayedCategories = showAllCategories
    ? baseCategories
    : baseCategories.filter((cat) => cat.spending > 0)

  const hasUnusedCategories = baseCategories.some((cat) => cat.spending === 0)

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 sm:p-6 space-y-6 sm:space-y-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">
              Dashboard
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <button
                onClick={goToPreviousMonth}
                className={cn(
                  'p-1 rounded-md',
                  'text-[var(--text-muted)]',
                  'hover:bg-[var(--surface-hover)]',
                  'hover:text-[var(--text-primary)]',
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
                    ? 'text-[var(--text-primary)]'
                    : 'text-[var(--accent-primary)] hover:underline'
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
                    ? 'text-[var(--text-muted)] opacity-50 cursor-not-allowed'
                    : 'text-[var(--text-muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]'
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
              'text-[var(--text-muted)]',
              'hover:bg-[var(--surface-hover)]',
              'hover:text-[var(--text-primary)]',
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
                <p className="text-sm text-[var(--text-muted)] mb-1">
                  Remaining
                </p>
                <span className="text-3xl font-semibold text-[var(--text-primary)] tracking-tight">
                  {formatCurrency(budget.total_remaining)}
                </span>
              </div>
              <div className="text-right">
                <span className="text-sm text-[var(--text-muted)] block">
                  {budget.total_percentage.toFixed(0)}% used
                </span>
                {isCurrentMonthSelected && (
                  <div className="text-xs">
                    <span className={getPaceColorClass(calculatePace(budget.total_percentage, budget.year, budget.month))}>
                      {formatPace(calculatePace(budget.total_percentage, budget.year, budget.month))}
                    </span>
                    <span className="text-[var(--text-muted)] mx-1">|</span>
                    <span className={getPaceDiffColorClass(calculatePaceDifference(budget.total_spending, budget.total_cap, budget.year, budget.month))}>
                      {formatPaceDifference(calculatePaceDifference(budget.total_spending, budget.total_cap, budget.year, budget.month))}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <ProgressBar percentage={budget.total_percentage} />
            <div className="flex justify-between text-sm text-[var(--text-muted)]">
              <span>Spent: {formatCurrency(budget.total_spending)}</span>
              <span>Budget: {formatCurrency(budget.total_cap)}</span>
            </div>
            {isCurrentMonthSelected && (
              <div className="text-xs text-[var(--text-muted)] text-center pt-2 border-t border-[var(--border-primary)]">
                Day {new Date().getDate()} of {getDaysInMonth(budget.year, budget.month)} ({((new Date().getDate() / getDaysInMonth(budget.year, budget.month)) * 100).toFixed(0)}% through month)
              </div>
            )}
            {budget.excluded_categories && budget.excluded_categories.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] pt-1 border-t border-[var(--border-primary)]">
                <EyeOff className="h-3 w-3 flex-shrink-0" />
                <span>
                  Total excludes:{' '}
                  <span className="text-[var(--warning)]">
                    {budget.excluded_categories.map(catId => getCategoryDisplayName(catId, categories)).join(', ')}
                  </span>
                </span>
              </div>
            )}
            <div className="pt-1 border-t border-[var(--border-primary)]">
              <button
                onClick={() => setCalculatorOpen(true)}
                className={cn(
                  'flex items-center gap-1.5 text-xs',
                  'text-[var(--text-muted)]',
                  'hover:text-[var(--accent-primary)]',
                  'transition-colors'
                )}
                aria-label="Open budget calculator"
              >
                <Calculator className="h-3 w-3" />
                Help me set this
              </button>
            </div>
          </div>
        </Card>

        {baseCategories.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-[var(--text-primary)]">
                Category Breakdown
              </h2>
              {hasUnusedCategories && (
                <button
                  onClick={() => setShowAllCategories((v) => !v)}
                  className="text-xs text-[var(--accent-primary)] hover:underline"
                >
                  {showAllCategories ? 'Hide Unused' : 'Show All'}
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {displayedCategories.map((cat) => {
                const categoryInfo = getCategoryInfo(cat.category, categories)
                const displayName = getCategoryDisplayName(cat.category, categories)
                const isExcluded = budget.excluded_categories?.includes(cat.category)
                const isUnused = cat.spending === 0

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
                              ? `${categoryInfo.color}${isUnused ? '10' : '20'}`
                              : undefined,
                          }}
                        >
                          {categoryInfo ? (
                            <DynamicIcon
                              name={categoryInfo.icon}
                              className="h-5 w-5"
                              style={{ color: isUnused ? `${categoryInfo.color}80` : categoryInfo.color }}
                            />
                          ) : (
                            <CategoryIcon
                              category={cat.category}
                              className="h-5 w-5 text-[var(--text-muted)]"
                            />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className={cn(
                                'text-sm font-medium',
                                isUnused ? 'text-[var(--text-muted)]' : 'text-[var(--text-primary)]'
                              )}>
                                {displayName}
                              </span>
                              {isExcluded && (
                                <>
                                  <EyeOff className="h-3.5 w-3.5 text-[var(--warning)]" aria-hidden="true" />
                                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-medium">
                                    Excluded
                                  </span>
                                </>
                              )}
                            </div>
                            <span className="text-xs text-[var(--text-muted)]">
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
            {/* Edit Categories button */}
            <button
              onClick={() => navigate('/settings', { state: { tab: 'categories' } })}
              className={cn(
                'mt-3 w-full flex items-center justify-center gap-2',
                'py-2.5 rounded-lg text-sm font-medium',
                'bg-[var(--surface-primary)] border border-[var(--border-primary)]',
                'text-[var(--text-secondary)]',
                'hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]',
                'transition-colors'
              )}
            >
              <Tag className="h-3.5 w-3.5" />
              Edit Categories
            </button>
          </div>
        )}

        {baseCategories.length === 0 && (
          <Card padding="lg">
            <p className="text-center text-sm text-[var(--text-muted)]">
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

        {/* Tips Widget */}
        <TipsWidget />

        {/* Budget Calculator Modal */}
        <BudgetCalculatorModal
          open={calculatorOpen}
          onClose={() => setCalculatorOpen(false)}
          onApply={handleCalculatorApply}
        />
    </div>
  )
}
