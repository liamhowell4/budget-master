import { useState } from 'react'
import { cn } from '@/utils/cn'
import { Modal } from '@/components/ui/Modal'
import { DynamicIcon } from '@/components/ui/IconPicker'
import { AlertTriangle } from 'lucide-react'
import type { Category } from '@/types/category'

interface DeleteCategoryModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (reassignTo: string) => Promise<{ success: boolean; reassigned_count?: number; error?: string }>
  category: Category | null
  categories: Category[] // For reassignment options
}

export function DeleteCategoryModal({
  isOpen,
  onClose,
  onConfirm,
  category,
  categories,
}: DeleteCategoryModalProps) {
  const [reassignTo, setReassignTo] = useState('OTHER')
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filter out the category being deleted from reassignment options
  const reassignOptions = categories.filter(
    (c) => c.category_id !== category?.category_id
  )

  const handleConfirm = async () => {
    if (!category) return

    setDeleting(true)
    setError(null)

    try {
      const result = await onConfirm(reassignTo)

      if (result.success) {
        onClose()
      } else {
        setError(result.error || 'Failed to delete category')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setDeleting(false)
    }
  }

  if (!category) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Delete Category">
      <div className="space-y-4">
        {/* Warning */}
        <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20">
          <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800 dark:text-amber-200">
            <p className="font-medium">This action cannot be undone.</p>
            <p className="mt-1 text-amber-700 dark:text-amber-300">
              All expenses in this category will be reassigned to another category.
            </p>
          </div>
        </div>

        {/* Category being deleted */}
        <div className="p-3 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">Deleting:</p>
          <div className="flex items-center gap-3">
            <div
              className="p-2 rounded-lg"
              style={{ backgroundColor: `${category.color}20` }}
            >
              <DynamicIcon
                name={category.icon}
                className="h-5 w-5"
                style={{ color: category.color }}
              />
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {category.display_name}
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Budget: ${category.monthly_cap.toFixed(2)}/month
              </p>
            </div>
          </div>
        </div>

        {/* Reassignment selector */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Reassign expenses to:
          </label>
          <select
            value={reassignTo}
            onChange={(e) => setReassignTo(e.target.value)}
            className={cn(
              'w-full px-3 py-2 text-sm',
              'rounded-lg border',
              'bg-white dark:bg-neutral-900',
              'border-neutral-200 dark:border-neutral-700',
              'text-neutral-900 dark:text-neutral-100',
              'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
            )}
          >
            {reassignOptions.map((cat) => (
              <option key={cat.category_id} value={cat.category_id}>
                {cat.display_name}
              </option>
            ))}
          </select>
        </div>

        {/* Error message */}
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        {/* Action buttons */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={deleting}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              'text-neutral-600 dark:text-neutral-400',
              'hover:bg-neutral-100 dark:hover:bg-neutral-800',
              'disabled:opacity-50'
            )}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={deleting}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              'bg-red-600 text-white',
              'hover:bg-red-700',
              'disabled:opacity-50'
            )}
          >
            {deleting ? 'Deleting...' : 'Delete Category'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
