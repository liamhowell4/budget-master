import { useState, useMemo, useCallback } from 'react'
import { Card, Spinner, CategoryIcon, Badge, SegmentedControl, ExpenseEditModal } from '@/components/ui'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import { useExpenses, invalidateExpensesCache } from '@/hooks/useExpenses'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import { useRecurring } from '@/hooks/useRecurring'
import { usePending } from '@/hooks/usePending'
import { deleteExpense, updateExpense } from '@/services/expenseService'
import { Check, X, Trash2, Repeat, ArrowUpDown } from 'lucide-react'
import type { Expense } from '@/types/expense'
import type { RecurringExpense, PendingExpense } from '@/types/recurring'

type Tab = 'history' | 'recurring'

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

type SortOption = 'date-desc' | 'date-asc' | 'amount-desc' | 'amount-asc'

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'date-desc', label: 'Newest first' },
  { value: 'date-asc', label: 'Oldest first' },
  { value: 'amount-desc', label: 'Highest amount' },
  { value: 'amount-asc', label: 'Lowest amount' },
]

function getExpenseTime(expense: Expense): number {
  if (expense.timestamp) {
    return new Date(expense.timestamp).getTime()
  }
  // Fallback to date-only for older expenses without timestamp
  return new Date(expense.date.year, expense.date.month - 1, expense.date.day).getTime()
}

function sortExpenses(expenses: Expense[], sortBy: SortOption): Expense[] {
  return [...expenses].sort((a, b) => {
    switch (sortBy) {
      case 'date-desc':
        return getExpenseTime(b) - getExpenseTime(a)
      case 'date-asc':
        return getExpenseTime(a) - getExpenseTime(b)
      case 'amount-desc':
        return b.amount - a.amount
      case 'amount-asc':
        return a.amount - b.amount
      default:
        return 0
    }
  })
}

const FREQUENCY_LABELS: Record<string, string> = {
  monthly: 'Monthly',
  weekly: 'Weekly',
  biweekly: 'Bi-weekly',
  yearly: 'Yearly',
}

function getMonthOptions() {
  const now = new Date()
  const options = []
  for (let i = 0; i < 12; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
    options.push({
      value: `${date.getFullYear()}-${date.getMonth() + 1}`,
      label: date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
      year: date.getFullYear(),
      month: date.getMonth() + 1,
    })
  }
  return options
}

function ExpenseItem({ expense, onClick }: { expense: Expense; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 py-3 w-full text-left',
        'border-b border-[var(--border-primary)] last:border-0',
        'hover:bg-[var(--surface-hover)]',
        'transition-colors cursor-pointer'
      )}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-[var(--surface-secondary)]">
        <CategoryIcon
          category={expense.category}
          className="h-4 w-4 text-[var(--text-muted)]"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--text-primary)] truncate">
          {expense.expense_name}
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          {CATEGORY_LABELS[expense.category] || expense.category}
        </p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          {formatCurrency(expense.amount)}
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          {formatExpenseDate(expense.date)}
        </p>
      </div>
    </button>
  )
}


function PendingExpenseItem({
  pending,
  onConfirm,
  onSkip,
  isConfirming,
  isSkipping,
}: {
  pending: PendingExpense
  onConfirm: () => void
  onSkip: () => void
  isConfirming: boolean
  isSkipping: boolean
}) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-[var(--border-primary)] last:border-0">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-[var(--warning-muted)]">
        <CategoryIcon
          category={pending.category}
          className="h-4 w-4 text-[var(--warning)]"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--text-primary)] truncate">
          {pending.expense_name}
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          Awaiting confirmation
        </p>
      </div>
      <p className="text-sm font-medium text-[var(--text-primary)] mr-2">
        {formatCurrency(pending.amount)}
      </p>
      <div className="flex gap-1">
        <button
          onClick={onConfirm}
          disabled={isConfirming || isSkipping}
          className={cn(
            'flex h-7 w-7 items-center justify-center rounded-md',
            'bg-[var(--success-muted)] text-[var(--success)]',
            'hover:opacity-80',
            'disabled:opacity-50 transition-colors'
          )}
          aria-label="Confirm"
        >
          {isConfirming ? <Spinner size="sm" /> : <Check className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={onSkip}
          disabled={isConfirming || isSkipping}
          className={cn(
            'flex h-7 w-7 items-center justify-center rounded-md',
            'bg-[var(--error-muted)] text-[var(--error)]',
            'hover:opacity-80',
            'disabled:opacity-50 transition-colors'
          )}
          aria-label="Skip"
        >
          {isSkipping ? <Spinner size="sm" /> : <X className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  )
}

const DAY_OF_WEEK_LABELS: Record<number, string> = {
  0: 'Sunday',
  1: 'Monday',
  2: 'Tuesday',
  3: 'Wednesday',
  4: 'Thursday',
  5: 'Friday',
  6: 'Saturday',
}

function getOrdinalSuffix(n: number): string {
  if (n >= 11 && n <= 13) return 'th'
  switch (n % 10) {
    case 1: return 'st'
    case 2: return 'nd'
    case 3: return 'rd'
    default: return 'th'
  }
}

const MONTH_LABELS: Record<number, string> = {
  1: 'January', 2: 'February', 3: 'March', 4: 'April',
  5: 'May', 6: 'June', 7: 'July', 8: 'August',
  9: 'September', 10: 'October', 11: 'November', 12: 'December',
}

function formatSchedule(recurring: RecurringExpense): string {
  const { frequency, day_of_month, day_of_week, month_of_year, last_of_month } = recurring

  if (frequency === 'monthly') {
    if (last_of_month) {
      return 'Last day of month'
    }
    if (day_of_month) {
      return `${day_of_month}${getOrdinalSuffix(day_of_month)} of each month`
    }
    return 'Monthly'
  }

  if (frequency === 'weekly') {
    if (day_of_week !== null && day_of_week !== undefined) {
      return `Every ${DAY_OF_WEEK_LABELS[day_of_week] || 'week'}`
    }
    return 'Weekly'
  }

  if (frequency === 'biweekly') {
    if (day_of_week !== null && day_of_week !== undefined) {
      return `Every other ${DAY_OF_WEEK_LABELS[day_of_week] || 'week'}`
    }
    return 'Every 2 weeks'
  }

  if (frequency === 'yearly') {
    const monthName = month_of_year ? MONTH_LABELS[month_of_year] : ''
    if (last_of_month && monthName) {
      return `Last day of ${monthName}`
    }
    if (day_of_month && monthName) {
      return `${monthName} ${day_of_month}${getOrdinalSuffix(day_of_month)}`
    }
    return 'Yearly'
  }

  return FREQUENCY_LABELS[frequency] || frequency
}

function RecurringItem({
  recurring,
  onDelete,
  isDeleting,
}: {
  recurring: RecurringExpense
  onDelete: () => void
  isDeleting: boolean
}) {
  const [isConfirming, setIsConfirming] = useState(false)
  const schedule = formatSchedule(recurring)

  const handleDeleteClick = () => {
    setIsConfirming(true)
  }

  const handleConfirmDelete = () => {
    setIsConfirming(false)
    onDelete()
  }

  const handleCancelDelete = () => {
    setIsConfirming(false)
  }

  return (
    <div className="flex items-center gap-3 py-3 border-b border-[var(--border-primary)] last:border-0">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-[var(--accent-muted)]">
        <CategoryIcon
          category={recurring.category}
          className="h-4 w-4 text-[var(--accent-primary)]"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--text-primary)] truncate">
          {recurring.expense_name}
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <Repeat className="h-3 w-3" />
          <span>{schedule}</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            {formatCurrency(recurring.amount)}
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            {CATEGORY_LABELS[recurring.category] || recurring.category}
          </p>
        </div>
        {isConfirming ? (
          <div className="flex items-center gap-1">
            <button
              onClick={handleCancelDelete}
              disabled={isDeleting}
              className={cn(
                'flex h-7 w-7 items-center justify-center rounded-md',
                'text-[var(--text-muted)]',
                'hover:bg-[var(--surface-hover)]',
                'disabled:opacity-50 transition-colors'
              )}
              aria-label="Cancel"
            >
              <X className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className={cn(
                'flex h-7 w-7 items-center justify-center rounded-md',
                'bg-[var(--error)] text-[var(--text-inverted)]',
                'hover:opacity-80',
                'disabled:opacity-50 transition-colors'
              )}
              aria-label="Confirm delete"
            >
              {isDeleting ? <Spinner size="sm" /> : <Check className="h-3.5 w-3.5" />}
            </button>
          </div>
        ) : (
          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className={cn(
              'flex h-7 w-7 items-center justify-center rounded-md',
              'text-[var(--text-muted)]',
              'hover:bg-[var(--error-muted)] hover:text-[var(--error)]',
              'disabled:opacity-50 transition-colors'
            )}
            aria-label="Delete"
          >
            {isDeleting ? <Spinner size="sm" /> : <Trash2 className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
    </div>
  )
}

export function ExpensesPage() {
  const [activeTab, setActiveTab] = useState<Tab>('history')
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${now.getMonth() + 1}`
  })
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [sortBy, setSortBy] = useState<SortOption>('date-desc')
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [skippingId, setSkippingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null)

  const monthOptions = useMemo(() => getMonthOptions(), [])
  const selectedMonthData = useMemo(
    () => monthOptions.find((m) => m.value === selectedMonth),
    [monthOptions, selectedMonth]
  )

  const categoryFilter = selectedCategory === 'all' ? undefined : selectedCategory

  const {
    expenses,
    loading: expensesLoading,
    error: expensesError,
  } = useExpenses(
    selectedMonthData?.year,
    selectedMonthData?.month,
    categoryFilter
  )

  const {
    recurring,
    loading: recurringLoading,
    error: recurringError,
    deleteTemplate,
  } = useRecurring()

  const {
    pending,
    loading: pendingLoading,
    confirm: confirmPending,
    skip: skipPending,
  } = usePending()

  const handleConfirm = async (pendingId: string) => {
    setConfirmingId(pendingId)
    try {
      await confirmPending(pendingId)
    } finally {
      setConfirmingId(null)
    }
  }

  const handleSkip = async (pendingId: string) => {
    setSkippingId(pendingId)
    try {
      await skipPending(pendingId)
    } finally {
      setSkippingId(null)
    }
  }

  const handleDelete = async (templateId: string) => {
    setDeletingId(templateId)
    try {
      await deleteTemplate(templateId)
    } finally {
      setDeletingId(null)
    }
  }

  const handleExpenseSave = useCallback(
    async (expenseId: string, updates: { expense_name?: string; amount?: number; category?: string; date?: { day: number; month: number; year: number }; timestamp?: string }) => {
      await updateExpense(expenseId, updates)
      invalidateExpensesCache()
      invalidateBudgetCache()
    },
    []
  )

  const handleExpenseDelete = useCallback(async (expenseId: string) => {
    await deleteExpense(expenseId)
    invalidateExpensesCache()
    invalidateBudgetCache()
  }, [])

  const availableCategories = useMemo(() => {
    const cats = new Set(expenses.map((e) => e.category))
    return Array.from(cats).sort()
  }, [expenses])

  const sortedExpenses = useMemo(
    () => sortExpenses(expenses, sortBy),
    [expenses, sortBy]
  )

  // Filter to only show active recurring expenses
  const activeRecurring = useMemo(() => {
    return recurring.filter((r) => r.active)
  }, [recurring])

  return (
    <div className="h-[calc(100dvh-56px)] flex flex-col overflow-hidden">
      <div className="max-w-4xl mx-auto w-full px-4 pt-6 sm:px-6 flex flex-col flex-1 min-h-0">
        {/* Page header */}
        <div className="mb-4 flex-shrink-0">
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">
            Expenses
          </h1>
        </div>

        {/* Tabs */}
        <div className="mb-4 flex-shrink-0">
          <SegmentedControl
            options={[
              { value: 'history', label: 'History' },
              {
                value: 'recurring',
                label: 'Recurring',
                badge: activeRecurring.length > 0 ? (
                  <Badge variant="default">{activeRecurring.length}</Badge>
                ) : undefined,
              },
            ]}
            value={activeTab}
            onChange={(tab) => setActiveTab(tab as Tab)}
          />
        </div>

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="flex flex-col flex-1 min-h-0 space-y-4">
            {/* Pending Expenses */}
            {!pendingLoading && pending.length > 0 && (
              <Card className="flex-shrink-0">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-[var(--text-primary)]">
                    Pending Confirmation
                  </h3>
                  <Badge variant="warning">{pending.length}</Badge>
                </div>
                <div>
                  {pending.map((p) => (
                    <PendingExpenseItem
                      key={p.pending_id}
                      pending={p}
                      onConfirm={() => handleConfirm(p.pending_id)}
                      onSkip={() => handleSkip(p.pending_id)}
                      isConfirming={confirmingId === p.pending_id}
                      isSkipping={skippingId === p.pending_id}
                    />
                  ))}
                </div>
              </Card>
            )}

            {/* Filters */}
            <div className="flex flex-wrap gap-2 sm:gap-3 flex-shrink-0">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className={cn(
                  'h-9 rounded-md px-3 text-sm min-w-0',
                  'bg-[var(--bg-secondary)]',
                  'border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:border-[var(--border-focus)]'
                )}
              >
                {monthOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className={cn(
                  'h-9 rounded-md px-3 text-sm min-w-0',
                  'bg-[var(--bg-secondary)]',
                  'border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:border-[var(--border-focus)]'
                )}
              >
                <option value="all">All Categories</option>
                {availableCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {CATEGORY_LABELS[cat] || cat}
                  </option>
                ))}
              </select>
              <div className="relative">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className={cn(
                    'appearance-none h-9 pl-8 pr-3 rounded-md text-sm',
                    'bg-[var(--bg-secondary)]',
                    'border border-[var(--border-primary)]',
                    'text-[var(--text-primary)]',
                    'focus:outline-none focus:border-[var(--border-focus)]'
                  )}
                >
                  {SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)] pointer-events-none" />
              </div>
            </div>

            {/* Expense List - Card with scrollable content */}
            {expensesLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : expensesError ? (
              <Card>
                <p className="text-center text-sm text-[var(--error)] py-4">
                  {expensesError}
                </p>
              </Card>
            ) : expenses.length === 0 ? (
              <Card>
                <div className="py-8 text-center">
                  <p className="text-sm text-[var(--text-muted)]">
                    No expenses found for this period
                  </p>
                </div>
              </Card>
            ) : (
              <Card className="flex-1 min-h-0 flex flex-col overflow-hidden !p-0">
                <div className="flex-1 overflow-y-auto px-4 py-1.5">
                  {sortedExpenses.map((expense) => (
                    <ExpenseItem
                      key={expense.id}
                      expense={expense}
                      onClick={() => setSelectedExpense(expense)}
                    />
                  ))}
                </div>
              </Card>
            )}
            {/* Bottom spacer - always visible */}
            <div className="h-6 flex-shrink-0" />
          </div>
        )}

        {/* Recurring Tab */}
        {activeTab === 'recurring' && (
          <div className="flex flex-col flex-1 min-h-0">
            <div className="flex-1 min-h-0 overflow-y-auto">
            {recurringLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : recurringError ? (
              <Card>
                <p className="text-center text-sm text-[var(--error)] py-4">
                  {recurringError}
                </p>
              </Card>
            ) : activeRecurring.length === 0 ? (
              <Card>
                <div className="py-8 text-center">
                  <Repeat className="h-8 w-8 mx-auto mb-3 text-[var(--text-muted)] opacity-50" />
                  <p className="text-sm text-[var(--text-muted)]">
                    No active recurring expenses
                  </p>
                  <p className="text-xs text-[var(--text-muted)] opacity-70 mt-1">
                    Use chat to create recurring expenses like rent or subscriptions
                  </p>
                </div>
              </Card>
            ) : (
              <Card>
                <div className="mb-3 pb-3 border-b border-[var(--border-primary)]">
                  <h3 className="text-sm font-medium text-[var(--text-primary)]">
                    Active Schedules
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    {activeRecurring.length} recurring expense{activeRecurring.length !== 1 ? 's' : ''}
                  </p>
                </div>
                {activeRecurring.map((rec) => (
                  <RecurringItem
                    key={rec.template_id}
                    recurring={rec}
                    onDelete={() => handleDelete(rec.template_id)}
                    isDeleting={deletingId === rec.template_id}
                  />
                ))}
              </Card>
            )}
            </div>
            {/* Bottom spacer - always visible */}
            <div className="h-6 flex-shrink-0" />
          </div>
        )}

        {/* Expense Detail Modal */}
        <ExpenseEditModal
          expense={selectedExpense}
          isOpen={selectedExpense !== null}
          onClose={() => setSelectedExpense(null)}
          onSave={handleExpenseSave}
          onDelete={handleExpenseDelete}
        />
      </div>
    </div>
  )
}
