import { useState, useMemo } from 'react'
import { Card, Spinner, CategoryIcon, Badge, Modal, SegmentedControl } from '@/components/ui'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import { useExpenses, invalidateExpensesCache } from '@/hooks/useExpenses'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import { useRecurring } from '@/hooks/useRecurring'
import { usePending } from '@/hooks/usePending'
import { deleteExpense, updateExpense } from '@/services/expenseService'
import { Check, X, Trash2, Repeat, Calendar, Clock, Pencil, ArrowUpDown } from 'lucide-react'
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

function sortExpenses(expenses: Expense[], sortBy: SortOption): Expense[] {
  return [...expenses].sort((a, b) => {
    switch (sortBy) {
      case 'date-desc':
        return new Date(b.date.year, b.date.month - 1, b.date.day).getTime() -
               new Date(a.date.year, a.date.month - 1, a.date.day).getTime()
      case 'date-asc':
        return new Date(a.date.year, a.date.month - 1, a.date.day).getTime() -
               new Date(b.date.year, b.date.month - 1, b.date.day).getTime()
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
        'border-b border-neutral-200 dark:border-neutral-800 last:border-0',
        'hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
        'transition-colors cursor-pointer'
      )}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-neutral-100 dark:bg-neutral-800">
        <CategoryIcon
          category={expense.category}
          className="h-4 w-4 text-neutral-500 dark:text-neutral-400"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
          {expense.expense_name}
        </p>
        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          {CATEGORY_LABELS[expense.category] || expense.category}
        </p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {formatCurrency(expense.amount)}
        </p>
        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          {formatExpenseDate(expense.date)}
        </p>
      </div>
    </button>
  )
}

function ExpenseDetailModal({
  expense,
  isOpen,
  onClose,
  onDeleted,
}: {
  expense: Expense | null
  isOpen: boolean
  onClose: () => void
  onDeleted?: () => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [editName, setEditName] = useState('')
  const [editAmount, setEditAmount] = useState('')

  // Reset state when modal opens/closes or expense changes
  const handleClose = () => {
    setIsEditing(false)
    setIsConfirmingDelete(false)
    setEditName('')
    setEditAmount('')
    onClose()
  }

  const handleStartEdit = () => {
    if (expense) {
      setEditName(expense.expense_name)
      setEditAmount(expense.amount.toString())
      setIsEditing(true)
    }
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
    setEditName('')
    setEditAmount('')
  }

  const handleSaveEdit = async () => {
    if (!expense) return
    const newAmount = parseFloat(editAmount)
    if (isNaN(newAmount)) return

    setIsSaving(true)
    try {
      await updateExpense(expense.id, {
        expense_name: editName !== expense.expense_name ? editName : undefined,
        amount: newAmount !== expense.amount ? newAmount : undefined,
      })
      invalidateExpensesCache()
      invalidateBudgetCache()
      handleClose()
    } catch (err) {
      console.error('Failed to update expense:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteClick = () => {
    setIsConfirmingDelete(true)
  }

  const handleCancelDelete = () => {
    setIsConfirmingDelete(false)
  }

  const handleConfirmDelete = async () => {
    if (!expense) return
    setIsDeleting(true)
    try {
      await deleteExpense(expense.id)
      invalidateExpensesCache()
      invalidateBudgetCache()
      onDeleted?.()
      handleClose()
    } catch (err) {
      console.error('Failed to delete expense:', err)
    } finally {
      setIsDeleting(false)
      setIsConfirmingDelete(false)
    }
  }

  if (!expense) return null

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Expense Details">
      <div className="space-y-6">
        {/* Amount - large display or edit input */}
        <div className="text-center py-4">
          {isEditing ? (
            <div className="flex items-center justify-center gap-2">
              <span className="text-2xl text-neutral-400">$</span>
              <input
                type="number"
                step="0.01"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                className={cn(
                  'w-32 px-3 py-2 text-2xl font-semibold text-center rounded-lg',
                  'bg-neutral-100 dark:bg-neutral-800',
                  'border border-neutral-300 dark:border-neutral-600',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500',
                  'text-neutral-900 dark:text-neutral-100'
                )}
              />
            </div>
          ) : (
            <p className="text-4xl font-semibold text-neutral-900 dark:text-neutral-100">
              {formatCurrency(expense.amount)}
            </p>
          )}
        </div>

        {/* Details */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
              <CategoryIcon
                category={expense.category}
                className="h-5 w-5 text-neutral-600 dark:text-neutral-300"
              />
            </div>
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Category</p>
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {CATEGORY_LABELS[expense.category] || expense.category}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
              <Calendar className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
            </div>
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Date</p>
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {formatExpenseDate(expense.date)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
              {expense.input_type === 'recurring' ? (
                <Repeat className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
              ) : (
                <Clock className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
              )}
            </div>
            <div className="flex-1">
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Description</p>
              {isEditing ? (
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className={cn(
                    'w-full px-2 py-1 text-sm rounded-md mt-1',
                    'bg-white dark:bg-neutral-700',
                    'border border-neutral-300 dark:border-neutral-600',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500',
                    'text-neutral-900 dark:text-neutral-100'
                  )}
                />
              ) : (
                <>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    {expense.expense_name}
                  </p>
                  {expense.input_type && (
                    <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
                      {expense.input_type === 'recurring' ? 'Recurring expense' : 'Manual entry'}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
          {isEditing ? (
            <>
              <button
                onClick={handleCancelEdit}
                disabled={isSaving}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-neutral-100 dark:bg-neutral-800',
                  'text-neutral-600 dark:text-neutral-400',
                  'hover:bg-neutral-200 dark:hover:bg-neutral-700',
                  'disabled:opacity-50 transition-colors'
                )}
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={isSaving}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-blue-500 text-white',
                  'hover:bg-blue-600',
                  'disabled:opacity-50 transition-colors'
                )}
              >
                {isSaving ? <Spinner size="sm" /> : <Check className="h-4 w-4" />}
                Save
              </button>
            </>
          ) : isConfirmingDelete ? (
            <>
              <button
                onClick={handleCancelDelete}
                disabled={isDeleting}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-neutral-100 dark:bg-neutral-800',
                  'text-neutral-600 dark:text-neutral-400',
                  'hover:bg-neutral-200 dark:hover:bg-neutral-700',
                  'disabled:opacity-50 transition-colors'
                )}
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-red-500 text-white',
                  'hover:bg-red-600',
                  'disabled:opacity-50 transition-colors'
                )}
              >
                {isDeleting ? <Spinner size="sm" /> : <Check className="h-4 w-4" />}
                Confirm Delete
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleStartEdit}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-neutral-100 dark:bg-neutral-800',
                  'text-neutral-600 dark:text-neutral-400',
                  'hover:bg-neutral-200 dark:hover:bg-neutral-700',
                  'transition-colors'
                )}
              >
                <Pencil className="h-4 w-4" />
                Edit
              </button>
              <button
                onClick={handleDeleteClick}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-neutral-100 dark:bg-neutral-800',
                  'text-red-600 dark:text-red-400',
                  'hover:bg-red-100 dark:hover:bg-red-900/30',
                  'transition-colors'
                )}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            </>
          )}
        </div>
      </div>
    </Modal>
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
    <div className="flex items-center gap-3 py-3 border-b border-neutral-200 dark:border-neutral-800 last:border-0">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-amber-100 dark:bg-amber-900/30">
        <CategoryIcon
          category={pending.category}
          className="h-4 w-4 text-amber-600 dark:text-amber-400"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
          {pending.expense_name}
        </p>
        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          Awaiting confirmation
        </p>
      </div>
      <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mr-2">
        {formatCurrency(pending.amount)}
      </p>
      <div className="flex gap-1">
        <button
          onClick={onConfirm}
          disabled={isConfirming || isSkipping}
          className={cn(
            'flex h-7 w-7 items-center justify-center rounded-md',
            'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
            'hover:bg-emerald-200 dark:hover:bg-emerald-900/50',
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
            'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
            'hover:bg-red-200 dark:hover:bg-red-900/50',
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

function formatSchedule(recurring: RecurringExpense): string {
  const { frequency, day_of_month, day_of_week, last_of_month } = recurring

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
    <div className="flex items-center gap-3 py-3 border-b border-neutral-200 dark:border-neutral-800 last:border-0">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-blue-100 dark:bg-blue-900/30">
        <CategoryIcon
          category={recurring.category}
          className="h-4 w-4 text-blue-600 dark:text-blue-400"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
          {recurring.expense_name}
        </p>
        <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-500">
          <Repeat className="h-3 w-3" />
          <span>{schedule}</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            {formatCurrency(recurring.amount)}
          </p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500">
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
                'text-neutral-400 dark:text-neutral-500',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
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
                'bg-red-500 text-white',
                'hover:bg-red-600',
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
              'text-neutral-400 dark:text-neutral-500',
              'hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 dark:hover:text-red-400',
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
    <div className="max-w-4xl mx-auto px-4 py-6 sm:p-6 overflow-x-hidden">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            Expenses
          </h1>
        </div>

        {/* Tabs */}
        <div className="mb-6">
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
          <div className="space-y-6">
            {/* Pending Expenses */}
            {!pendingLoading && pending.length > 0 && (
              <Card>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
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
            <div className="flex flex-wrap gap-2 sm:gap-3">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className={cn(
                  'h-9 rounded-md px-3 text-sm min-w-0',
                  'bg-neutral-50 dark:bg-neutral-900',
                  'border border-neutral-200 dark:border-neutral-800',
                  'text-neutral-900 dark:text-neutral-100',
                  'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600'
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
                  'bg-neutral-50 dark:bg-neutral-900',
                  'border border-neutral-200 dark:border-neutral-800',
                  'text-neutral-900 dark:text-neutral-100',
                  'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600'
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
                    'bg-neutral-50 dark:bg-neutral-900',
                    'border border-neutral-200 dark:border-neutral-800',
                    'text-neutral-900 dark:text-neutral-100',
                    'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600'
                  )}
                >
                  {SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 pointer-events-none" />
              </div>
            </div>

            {/* Expense List */}
            {expensesLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : expensesError ? (
              <Card>
                <p className="text-center text-sm text-red-500 py-4">
                  {expensesError}
                </p>
              </Card>
            ) : expenses.length === 0 ? (
              <Card>
                <div className="py-8 text-center">
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">
                    No expenses found for this period
                  </p>
                </div>
              </Card>
            ) : (
              <Card>
                {sortedExpenses.map((expense) => (
                  <ExpenseItem
                    key={expense.id}
                    expense={expense}
                    onClick={() => setSelectedExpense(expense)}
                  />
                ))}
              </Card>
            )}
          </div>
        )}

        {/* Recurring Tab */}
        {activeTab === 'recurring' && (
          <div className="space-y-6">
            {recurringLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : recurringError ? (
              <Card>
                <p className="text-center text-sm text-red-500 py-4">
                  {recurringError}
                </p>
              </Card>
            ) : activeRecurring.length === 0 ? (
              <Card>
                <div className="py-8 text-center">
                  <Repeat className="h-8 w-8 mx-auto mb-3 text-neutral-300 dark:text-neutral-600" />
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">
                    No active recurring expenses
                  </p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                    Use chat to create recurring expenses like rent or subscriptions
                  </p>
                </div>
              </Card>
            ) : (
              <Card>
                <div className="mb-3 pb-3 border-b border-neutral-200 dark:border-neutral-800">
                  <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    Active Schedules
                  </h3>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
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
        )}

        {/* Expense Detail Modal */}
        <ExpenseDetailModal
          expense={selectedExpense}
          isOpen={selectedExpense !== null}
          onClose={() => setSelectedExpense(null)}
          onDeleted={() => setSelectedExpense(null)}
        />
    </div>
  )
}
