import { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/utils/cn'
import { DynamicIcon } from '@/components/ui/IconPicker'
import { CategoryModal } from './CategoryModal'
import { DeleteCategoryModal } from './DeleteCategoryModal'
import { Plus, GripVertical, Pencil, Trash2, Lock, EyeOff } from 'lucide-react'
import { useCategories } from '@/hooks/useCategories'
import { Spinner } from '@/components/ui/Spinner'
import { Reorder, useDragControls, motion } from 'framer-motion'
import type { Category, CategoryCreate, CategoryUpdate } from '@/types/category'

// Debounce hook
function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  return useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      timeoutRef.current = setTimeout(() => {
        callback(...args)
      }, delay)
    }) as T,
    [callback, delay]
  )
}

interface CategoryItemProps {
  category: Category
  onEdit: () => void
  onDelete: () => void
  onToggleExclude: () => void
}

function CategoryItem({ category, onEdit, onDelete, onToggleExclude }: CategoryItemProps) {
  const dragControls = useDragControls()

  return (
    <Reorder.Item
      value={category}
      dragListener={!category.is_system}
      dragControls={dragControls}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.15 }}
      whileDrag={{
        scale: 1.02,
        boxShadow: '0 8px 20px rgba(0,0,0,0.15)',
        zIndex: 50,
      }}
      className={cn(
        'flex items-center gap-3 p-3',
        'rounded-xl border',
        'bg-white dark:bg-neutral-900',
        'border-neutral-200 dark:border-neutral-800',
        !category.is_system && 'cursor-grab active:cursor-grabbing'
      )}
    >
      {/* Drag handle */}
      <motion.div
        onPointerDown={(e) => {
          if (!category.is_system) {
            dragControls.start(e)
          }
        }}
        className={cn(
          'touch-none',
          category.is_system
            ? 'text-neutral-300 dark:text-neutral-700 cursor-not-allowed'
            : 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-grab active:cursor-grabbing'
        )}
      >
        <GripVertical className="h-4 w-4" />
      </motion.div>

      {/* Icon */}
      <div
        className="p-2 rounded-lg flex-shrink-0"
        style={{ backgroundColor: `${category.color}20` }}
      >
        <DynamicIcon
          name={category.icon}
          className="h-5 w-5"
          style={{ color: category.color }}
        />
      </div>

      {/* Name and budget */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
            {category.display_name}
          </p>
          {category.is_system && (
            <Lock className="h-3 w-3 text-neutral-400 flex-shrink-0" />
          )}
          {category.exclude_from_total && (
            <span title="Excluded from total">
              <EyeOff className="h-3 w-3 text-amber-500 flex-shrink-0" />
            </span>
          )}
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          ${category.monthly_cap.toFixed(2)}/month
          {category.exclude_from_total && (
            <span className="ml-1 text-amber-600 dark:text-amber-400">(excluded from total)</span>
          )}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {/* Exclude from total toggle */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggleExclude()
          }}
          className={cn(
            'p-2 rounded-lg transition-colors',
            category.exclude_from_total
              ? 'text-amber-500 hover:text-amber-600 bg-amber-50 dark:bg-amber-900/20'
              : 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
          )}
          title={category.exclude_from_total ? 'Include in total budget' : 'Exclude from total budget'}
        >
          <EyeOff className="h-4 w-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onEdit()
          }}
          className={cn(
            'p-2 rounded-lg transition-colors',
            'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300',
            'hover:bg-neutral-100 dark:hover:bg-neutral-800'
          )}
          title="Edit"
        >
          <Pencil className="h-4 w-4" />
        </button>
        {!category.is_system && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className={cn(
              'p-2 rounded-lg transition-colors',
              'text-neutral-400 hover:text-red-600 dark:hover:text-red-400',
              'hover:bg-red-50 dark:hover:bg-red-900/20'
            )}
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </Reorder.Item>
  )
}

export function CategoriesTab() {
  const {
    categories,
    totalMonthlyBudget,
    maxCategories,
    loading,
    error,
    createCategory,
    updateCategory,
    deleteCategory,
    reorderCategories,
    updateTotalBudget,
    getAvailableBudget,
  } = useCategories()

  const [localCategories, setLocalCategories] = useState<Category[]>([])
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingBudget, setEditingBudget] = useState(false)
  const [budgetInput, setBudgetInput] = useState('')
  const [budgetError, setBudgetError] = useState<string | null>(null)

  // Sync local categories with server categories
  useEffect(() => {
    setLocalCategories(categories)
  }, [categories])

  // Debounced save function - saves 300ms after last reorder
  const debouncedSave = useDebounce(async (newOrder: Category[]) => {
    const categoryIds = newOrder.map((c) => c.category_id)
    try {
      await reorderCategories(categoryIds)
    } catch (err) {
      console.error('Failed to reorder categories:', err)
      // Revert to server state on error
      setLocalCategories(categories)
    }
  }, 300)

  const handleReorder = (newOrder: Category[]) => {
    // Update local state immediately for smooth animation
    setLocalCategories(newOrder)
    // Save to server after a short delay
    debouncedSave(newOrder)
  }

  const handleSaveCategory = async (data: CategoryCreate | CategoryUpdate) => {
    if (editingCategory) {
      return updateCategory(editingCategory.category_id, data as CategoryUpdate)
    } else {
      return createCategory(data as CategoryCreate)
    }
  }

  const handleDeleteCategory = async (reassignTo: string) => {
    if (deletingCategory) {
      return deleteCategory(deletingCategory.category_id, reassignTo)
    }
    return { success: false, error: 'No category selected' }
  }

  const handleToggleExclude = async (category: Category) => {
    const newValue = !category.exclude_from_total
    // Optimistically update local state
    setLocalCategories((prev) =>
      prev.map((c) =>
        c.category_id === category.category_id
          ? { ...c, exclude_from_total: newValue }
          : c
      )
    )
    // Save to server
    const result = await updateCategory(category.category_id, {
      exclude_from_total: newValue,
    })
    if (!result.success) {
      // Revert on error
      setLocalCategories((prev) =>
        prev.map((c) =>
          c.category_id === category.category_id
            ? { ...c, exclude_from_total: !newValue }
            : c
        )
      )
      console.error('Failed to toggle exclude from total:', result.error)
    }
  }

  const handleSaveBudget = async () => {
    const amount = parseFloat(budgetInput)
    if (isNaN(amount) || amount < 0) {
      setBudgetError('Please enter a valid amount')
      return
    }

    const result = await updateTotalBudget(amount)
    if (result.success) {
      setEditingBudget(false)
      setBudgetError(null)
    } else {
      setBudgetError(result.error || 'Failed to update budget')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    )
  }

  const existingNames = categories.map((c) => c.display_name)
  const availableBudget = getAvailableBudget()

  return (
    <div className="space-y-6">
      {/* Total Budget Section */}
      <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Total Monthly Budget
            </h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
              This is your overall spending limit
            </p>
          </div>
          {editingBudget ? (
            <div className="flex items-center gap-2">
              <div className="relative">
                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">$</span>
                <input
                  type="number"
                  value={budgetInput}
                  onChange={(e) => setBudgetInput(e.target.value)}
                  className={cn(
                    'w-28 pl-6 pr-2 py-1.5 text-sm',
                    'rounded-lg border',
                    'bg-white dark:bg-neutral-800',
                    'border-neutral-200 dark:border-neutral-700',
                    'text-neutral-900 dark:text-neutral-100',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
                  )}
                  autoFocus
                />
              </div>
              <button
                onClick={handleSaveBudget}
                className="px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setEditingBudget(false)
                  setBudgetError(null)
                }}
                className="px-3 py-1.5 text-sm text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => {
                setBudgetInput(totalMonthlyBudget.toString())
                setEditingBudget(true)
              }}
              className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              ${totalMonthlyBudget.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </button>
          )}
        </div>
        {budgetError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{budgetError}</p>
        )}
        <div className="mt-3 flex items-center gap-4 text-xs">
          <span className="text-neutral-500 dark:text-neutral-400">
            Allocated: ${(totalMonthlyBudget - availableBudget).toFixed(2)}
          </span>
          <span className="text-green-600 dark:text-green-400">
            Available: ${availableBudget.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Categories Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Categories ({categories.length}/{maxCategories})
          </h3>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
            Drag to reorder. Click to edit.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          disabled={categories.length >= maxCategories}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5',
            'text-sm font-medium rounded-lg transition-colors',
            'bg-blue-600 text-white',
            'hover:bg-blue-700',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <Plus className="h-4 w-4" />
          Add Category
        </button>
      </div>

      {/* Categories List with Framer Motion Reorder */}
      <Reorder.Group
        axis="y"
        values={localCategories}
        onReorder={handleReorder}
        className="space-y-2"
        layoutScroll
      >
        {localCategories.map((category) => (
          <CategoryItem
            key={category.category_id}
            category={category}
            onEdit={() => setEditingCategory(category)}
            onDelete={() => setDeletingCategory(category)}
            onToggleExclude={() => handleToggleExclude(category)}
          />
        ))}
      </Reorder.Group>

      {/* Create/Edit Modal */}
      <CategoryModal
        isOpen={showCreateModal || !!editingCategory}
        onClose={() => {
          setShowCreateModal(false)
          setEditingCategory(null)
        }}
        onSave={handleSaveCategory}
        category={editingCategory}
        availableBudget={availableBudget}
        existingNames={existingNames}
      />

      {/* Delete Modal */}
      <DeleteCategoryModal
        isOpen={!!deletingCategory}
        onClose={() => setDeletingCategory(null)}
        onConfirm={handleDeleteCategory}
        category={deletingCategory}
        categories={categories}
      />
    </div>
  )
}
