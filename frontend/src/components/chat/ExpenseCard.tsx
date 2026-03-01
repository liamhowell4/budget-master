import { useState } from 'react'
import { Pencil, Trash2, Check, X, ChevronDown } from 'lucide-react'
import { cn } from '@/utils/cn'
import { CATEGORY_COLORS, CATEGORY_LABELS } from '@/utils/constants'
import { CategoryIcon } from '@/components/ui/CategoryIcon'
import { useCategories } from '@/hooks/useCategories'
import type { ExpenseType } from '@/types/expense'

// Result from save_expense MCP tool
interface SaveExpenseResult {
  success: boolean
  expense_id: string
  expense_name: string
  amount: number
  category: string
  date?: { day: number; month: number; year: number }
}

interface BudgetAlert {
  type: 'info' | 'warning' | 'danger' | 'over'
  message: string
}

interface ExpenseCardProps {
  result: SaveExpenseResult
  budgetWarning?: string
  initialDeleted?: boolean
  onDelete?: (expenseId: string) => void
  onEdit?: (expenseId: string, updates: { name?: string; amount?: number; category?: string }) => void
}

// Parse budget warning string into structured alerts
function parseBudgetWarning(warning?: string): BudgetAlert[] {
  if (!warning || warning.trim() === '') return []

  const alerts: BudgetAlert[] = []
  const lines = warning.split('\n').filter((line) => line.trim())

  for (const line of lines) {
    let type: BudgetAlert['type'] = 'info'
    // Remove emoji prefixes for clean message
    let message = line.replace(/^[🚨⚠️ℹ️]\s*/, '').trim()

    if (line.includes('OVER BUDGET')) {
      type = 'over'
    } else if (line.startsWith('⚠️')) {
      // Check percentage to distinguish warning (90-94%) from danger (95-99%)
      const percentMatch = line.match(/(\d+)%/)
      if (percentMatch) {
        const percent = parseInt(percentMatch[1], 10)
        type = percent >= 95 ? 'danger' : 'warning'
      } else {
        type = 'warning'
      }
    } else if (line.startsWith('ℹ️')) {
      type = 'info'
    }

    alerts.push({ type, message })
  }

  return alerts
}

export function ExpenseCard({ result, budgetWarning, initialDeleted, onDelete, onEdit }: ExpenseCardProps) {
  const { categories } = useCategories()
  const [isEditing, setIsEditing] = useState(false)
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [editName, setEditName] = useState(result.expense_name)
  const [editAmount, setEditAmount] = useState(result.amount.toString())
  const [editCategory, setEditCategory] = useState(result.category)
  const [isCategoryOpen, setIsCategoryOpen] = useState(false)
  const [isDeleted, setIsDeleted] = useState(initialDeleted ?? false)

  const category = (isEditing ? editCategory : result.category) as ExpenseType
  const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.OTHER
  const label = CATEGORY_LABELS[category] ?? 'Other'
  const budgetAlerts = parseBudgetWarning(budgetWarning)
  const selectedCat = categories.find((c) => c.category_id === editCategory)

  const formatDate = () => {
    if (!result.date) {
      return 'Today'
    }
    const { day, month, year } = result.date
    const date = new Date(year, month - 1, day)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === today.toDateString()) return 'Today'
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const handleDeleteClick = () => {
    setIsConfirmingDelete(true)
  }

  const handleConfirmDelete = () => {
    setIsDeleted(true)
    setIsConfirmingDelete(false)
    onDelete?.(result.expense_id)
  }

  const handleCancelDelete = () => {
    setIsConfirmingDelete(false)
  }

  const handleSaveEdit = () => {
    const newAmount = parseFloat(editAmount)
    if (isNaN(newAmount)) return

    onEdit?.(result.expense_id, {
      name: editName !== result.expense_name ? editName : undefined,
      amount: newAmount !== result.amount ? newAmount : undefined,
      category: editCategory !== result.category ? editCategory : undefined,
    })
    setIsEditing(false)
    setIsCategoryOpen(false)
  }

  const handleCancelEdit = () => {
    setEditName(result.expense_name)
    setEditAmount(result.amount.toString())
    setEditCategory(result.category)
    setIsEditing(false)
    setIsCategoryOpen(false)
  }

  if (isDeleted) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)] py-2">
        <Trash2 className="h-3.5 w-3.5" />
        <span className="line-through">{result.expense_name}</span>
        <span>deleted</span>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-xl p-4 max-w-sm',
        'border border-[var(--border-primary)]/50',
        'transition-all duration-200',
        colors.bg
      )}
    >
      {/* Header: Category badge */}
      <div className="flex items-center justify-between mb-3">
        <div className={cn('flex items-center gap-1.5', colors.accent)}>
          <CategoryIcon category={category} className="h-4 w-4" />
          <span className="text-xs font-medium">{label}</span>
        </div>
        <span className="text-xs text-[var(--text-muted)]">
          {formatDate()}
        </span>
      </div>

      {/* Main content */}
      {isEditing ? (
        <div className="space-y-3">
          <input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            className={cn(
              'w-full px-2 py-1 text-sm rounded-md',
              'bg-[var(--bg-elevated)]',
              'border border-[var(--border-secondary)]',
              'focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]',
              'text-[var(--text-primary)]'
            )}
          />
          <div className="flex items-center gap-2">
            <span className="text-[var(--text-muted)]">$</span>
            <input
              type="number"
              step="0.01"
              value={editAmount}
              onChange={(e) => setEditAmount(e.target.value)}
              className={cn(
                'w-24 px-2 py-1 text-sm rounded-md',
                'bg-[var(--bg-elevated)]',
                'border border-[var(--border-secondary)]',
                'focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]',
                'text-[var(--text-primary)]'
              )}
            />
          </div>
          {/* Category dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsCategoryOpen(!isCategoryOpen)}
              className={cn(
                'w-full flex items-center justify-between px-2 py-1.5 rounded-md text-sm',
                'bg-[var(--bg-elevated)]',
                'border border-[var(--border-secondary)]',
                'focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]',
                'text-[var(--text-primary)]'
              )}
            >
              <div className="flex items-center gap-2">
                {selectedCat && (
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: selectedCat.color }}
                  />
                )}
                <span>{selectedCat?.display_name || editCategory}</span>
              </div>
              <ChevronDown
                className={cn(
                  'h-3.5 w-3.5 text-[var(--text-muted)] transition-transform',
                  isCategoryOpen && 'rotate-180'
                )}
              />
            </button>
            {isCategoryOpen && (
              <div
                className={cn(
                  'absolute z-10 mt-1 w-full max-h-40 overflow-y-auto rounded-md',
                  'bg-[var(--surface-primary)]',
                  'border border-[var(--border-primary)]',
                  'shadow-lg'
                )}
              >
                {categories.map((cat) => (
                  <button
                    key={cat.category_id}
                    type="button"
                    onClick={() => {
                      setEditCategory(cat.category_id)
                      setIsCategoryOpen(false)
                    }}
                    className={cn(
                      'w-full flex items-center gap-2 px-2 py-1.5 text-sm text-left',
                      'hover:bg-[var(--surface-hover)]',
                      'text-[var(--text-primary)]',
                      editCategory === cat.category_id && 'bg-[var(--surface-active)]'
                    )}
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: cat.color }}
                    />
                    <span>{cat.display_name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleSaveEdit}
              className={cn(
                'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                'bg-emerald-500/20 text-emerald-700 dark:text-emerald-400',
                'hover:bg-emerald-500/30 transition-colors'
              )}
            >
              <Check className="h-3 w-3" />
              Save
            </button>
            <button
              onClick={handleCancelEdit}
              className={cn(
                'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                'bg-neutral-500/20 text-neutral-600 dark:text-neutral-400',
                'hover:bg-neutral-500/30 transition-colors'
              )}
            >
              <X className="h-3 w-3" />
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="text-base font-medium text-[var(--text-primary)] truncate pr-2">
              {result.expense_name}
            </h3>
            <span className="text-lg font-semibold text-[var(--text-primary)] tabular-nums">
              ${result.amount.toFixed(2)}
            </span>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-3 pt-3 border-t border-[var(--border-primary)]/50">
            {isConfirmingDelete ? (
              <>
                <span className="text-xs text-[var(--text-muted)] self-center mr-1">
                  Delete?
                </span>
                <button
                  onClick={handleCancelDelete}
                  className={cn(
                    'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                    'bg-[var(--surface-secondary)]',
                    'text-[var(--text-secondary)]',
                    'hover:bg-[var(--surface-hover)]',
                    'border border-[var(--border-primary)]/50',
                    'transition-colors'
                  )}
                >
                  <X className="h-3 w-3" />
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  className={cn(
                    'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                    'bg-red-500 text-white',
                    'hover:bg-red-600',
                    'transition-colors'
                  )}
                >
                  <Check className="h-3 w-3" />
                  Confirm
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setIsEditing(true)}
                  className={cn(
                    'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                    'bg-[var(--surface-secondary)]',
                    'text-[var(--text-secondary)]',
                    'hover:bg-[var(--surface-hover)]',
                    'border border-[var(--border-primary)]/50',
                    'transition-colors'
                  )}
                >
                  <Pencil className="h-3 w-3" />
                  Edit
                </button>
                <button
                  onClick={handleDeleteClick}
                  className={cn(
                    'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                    'bg-[var(--surface-secondary)]',
                    'text-red-600 dark:text-red-400',
                    'hover:bg-red-50 dark:hover:bg-red-950/30',
                    'border border-[var(--border-primary)]/50',
                    'transition-colors'
                  )}
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </button>
              </>
            )}
          </div>
        </>
      )}

      {/* Budget alerts below the card */}
      {budgetAlerts.length > 0 && (
        <div className="mt-2 space-y-1">
          {budgetAlerts.map((alert, index) => (
            <div
              key={index}
              className={cn(
                'text-sm px-3 py-1.5 rounded-md',
                alert.type === 'over' && 'bg-red-500/10 text-red-600 dark:text-red-400',
                alert.type === 'danger' && 'bg-red-500/10 text-red-600 dark:text-red-400',
                alert.type === 'warning' && 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
                alert.type === 'info' && 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
              )}
            >
              {alert.message}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
