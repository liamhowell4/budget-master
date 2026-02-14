import { useState, useEffect } from 'react'
import { Modal } from './Modal'
import { Spinner } from './Spinner'
import { CategoryIcon } from './CategoryIcon'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDateTime } from '@/utils/formatters'
import { Check, X, Trash2, Pencil, Calendar, Clock, Repeat, ChevronDown } from 'lucide-react'
import { useCategories } from '@/hooks/useCategories'
import type { Expense } from '@/types/expense'

interface ExpenseEditModalProps {
  expense: Expense | null
  isOpen: boolean
  onClose: () => void
  onSave?: (expenseId: string, updates: { expense_name?: string; amount?: number; category?: string; date?: { day: number; month: number; year: number }; timestamp?: string }) => Promise<void>
  onDelete?: (expenseId: string) => Promise<void>
}

export function ExpenseEditModal({
  expense,
  isOpen,
  onClose,
  onSave,
  onDelete,
}: ExpenseEditModalProps) {
  const { categories, loading: categoriesLoading } = useCategories()
  const [isEditing, setIsEditing] = useState(false)
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [editName, setEditName] = useState('')
  const [editAmount, setEditAmount] = useState('')
  const [editCategory, setEditCategory] = useState('')
  const [editDate, setEditDate] = useState('')
  const [editTime, setEditTime] = useState('')
  const [isCategoryOpen, setIsCategoryOpen] = useState(false)

  // Reset state when modal opens/closes or expense changes
  useEffect(() => {
    if (expense && isOpen) {
      setEditName(expense.expense_name)
      setEditAmount(expense.amount.toString())
      setEditCategory(expense.category)
      // Initialize date as YYYY-MM-DD
      const d = expense.date
      setEditDate(`${d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`)
      // Initialize time from timestamp, or default to 12:00
      if (expense.timestamp) {
        const ts = new Date(expense.timestamp)
        setEditTime(`${String(ts.getHours()).padStart(2, '0')}:${String(ts.getMinutes()).padStart(2, '0')}`)
      } else {
        setEditTime('12:00')
      }
      setIsEditing(false)
      setIsConfirmingDelete(false)
      setIsCategoryOpen(false)
    }
  }, [expense, isOpen])

  const handleClose = () => {
    setIsEditing(false)
    setIsConfirmingDelete(false)
    setIsCategoryOpen(false)
    onClose()
  }

  const handleStartEdit = () => {
    if (expense) {
      setEditName(expense.expense_name)
      setEditAmount(expense.amount.toString())
      setEditCategory(expense.category)
      const d = expense.date
      setEditDate(`${d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`)
      if (expense.timestamp) {
        const ts = new Date(expense.timestamp)
        setEditTime(`${String(ts.getHours()).padStart(2, '0')}:${String(ts.getMinutes()).padStart(2, '0')}`)
      } else {
        setEditTime('12:00')
      }
      setIsEditing(true)
    }
  }

  const handleCancelEdit = () => {
    if (expense) {
      setEditName(expense.expense_name)
      setEditAmount(expense.amount.toString())
      setEditCategory(expense.category)
      const d = expense.date
      setEditDate(`${d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`)
      if (expense.timestamp) {
        const ts = new Date(expense.timestamp)
        setEditTime(`${String(ts.getHours()).padStart(2, '0')}:${String(ts.getMinutes()).padStart(2, '0')}`)
      } else {
        setEditTime('12:00')
      }
    }
    setIsEditing(false)
    setIsCategoryOpen(false)
  }

  const handleSaveEdit = async () => {
    if (!expense || !onSave) return
    const newAmount = parseFloat(editAmount)
    if (isNaN(newAmount)) return

    setIsSaving(true)
    try {
      const updates: { expense_name?: string; amount?: number; category?: string; date?: { day: number; month: number; year: number }; timestamp?: string } = {}
      if (editName !== expense.expense_name) updates.expense_name = editName
      if (newAmount !== expense.amount) updates.amount = newAmount
      if (editCategory !== expense.category) updates.category = editCategory

      // Check if date or time changed
      const origDate = `${expense.date.year}-${String(expense.date.month).padStart(2, '0')}-${String(expense.date.day).padStart(2, '0')}`
      let origTime = '12:00'
      if (expense.timestamp) {
        const ts = new Date(expense.timestamp)
        origTime = `${String(ts.getHours()).padStart(2, '0')}:${String(ts.getMinutes()).padStart(2, '0')}`
      }

      if (editDate !== origDate || editTime !== origTime) {
        // Parse the edited date and time
        const [yearStr, monthStr, dayStr] = editDate.split('-')
        const [hourStr, minStr] = editTime.split(':')
        const newDate = { day: parseInt(dayStr, 10), month: parseInt(monthStr, 10), year: parseInt(yearStr, 10) }
        updates.date = newDate
        // Construct ISO timestamp from date + time
        const dt = new Date(newDate.year, newDate.month - 1, newDate.day, parseInt(hourStr, 10), parseInt(minStr, 10))
        updates.timestamp = dt.toISOString()
      }

      if (Object.keys(updates).length > 0) {
        await onSave(expense.id, updates)
      }
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
    if (!expense || !onDelete) return
    setIsDeleting(true)
    try {
      await onDelete(expense.id)
      handleClose()
    } catch (err) {
      console.error('Failed to delete expense:', err)
    } finally {
      setIsDeleting(false)
      setIsConfirmingDelete(false)
    }
  }

  const getCategoryDisplay = (categoryId: string) => {
    const category = categories.find((c) => c.category_id === categoryId)
    return category?.display_name || categoryId
  }

  const selectedCategory = categories.find((c) => c.category_id === editCategory)

  if (!expense) return null

  const canEdit = !!onSave
  const canDelete = !!onDelete

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
          {/* Category - editable dropdown when in edit mode */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
              <CategoryIcon
                category={isEditing ? editCategory : expense.category}
                className="h-5 w-5 text-neutral-600 dark:text-neutral-300"
              />
            </div>
            <div className="flex-1">
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Category</p>
              {isEditing ? (
                <div className="relative mt-1">
                  <button
                    type="button"
                    onClick={() => setIsCategoryOpen(!isCategoryOpen)}
                    className={cn(
                      'w-full flex items-center justify-between px-3 py-2 rounded-md text-sm',
                      'bg-white dark:bg-neutral-700',
                      'border border-neutral-300 dark:border-neutral-600',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500',
                      'text-neutral-900 dark:text-neutral-100'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {selectedCategory && (
                        <span
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: selectedCategory.color }}
                        />
                      )}
                      <span>{getCategoryDisplay(editCategory)}</span>
                    </div>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 text-neutral-400 transition-transform',
                        isCategoryOpen && 'rotate-180'
                      )}
                    />
                  </button>
                  {isCategoryOpen && !categoriesLoading && (
                    <div
                      className={cn(
                        'absolute z-10 mt-1 w-full max-h-48 overflow-y-auto rounded-md',
                        'bg-white dark:bg-neutral-700',
                        'border border-neutral-200 dark:border-neutral-600',
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
                            'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                            'hover:bg-neutral-100 dark:hover:bg-neutral-600',
                            'text-neutral-900 dark:text-neutral-100',
                            editCategory === cat.category_id && 'bg-neutral-100 dark:bg-neutral-600'
                          )}
                        >
                          <span
                            className="w-3 h-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: cat.color }}
                          />
                          <span>{cat.display_name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {getCategoryDisplay(expense.category)}
                </p>
              )}
            </div>
          </div>

          {/* Date & Time */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
              <Calendar className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Date & Time</p>
              {isEditing ? (
                <div className="flex gap-2 mt-1">
                  <input
                    type="date"
                    value={editDate}
                    onChange={(e) => setEditDate(e.target.value)}
                    className={cn(
                      'flex-1 px-2 py-1 text-sm rounded-md',
                      'bg-white dark:bg-neutral-700',
                      'border border-neutral-300 dark:border-neutral-600',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500',
                      'text-neutral-900 dark:text-neutral-100'
                    )}
                  />
                  <input
                    type="time"
                    value={editTime}
                    onChange={(e) => setEditTime(e.target.value)}
                    className={cn(
                      'w-28 px-2 py-1 text-sm rounded-md',
                      'bg-white dark:bg-neutral-700',
                      'border border-neutral-300 dark:border-neutral-600',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500',
                      'text-neutral-900 dark:text-neutral-100'
                    )}
                  />
                </div>
              ) : (
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {formatExpenseDateTime(expense.date, expense.timestamp)}
                </p>
              )}
            </div>
          </div>

          {/* Description */}
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
        {(canEdit || canDelete) && (
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
                {canEdit && (
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
                )}
                {canDelete && (
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
                )}
              </>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}
