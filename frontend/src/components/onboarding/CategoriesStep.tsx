import { useState, useEffect } from 'react'
import { cn } from '@/utils/cn'
import { DynamicIcon } from '@/components/ui/IconPicker'
import { Check, Lock, Plus, X } from 'lucide-react'
import { categoryService } from '@/services/categoryService'
import { Spinner } from '@/components/ui/Spinner'
import { IconPicker } from '@/components/ui/IconPicker'
import { ColorPicker } from '@/components/ui/ColorPicker'
import type { DefaultCategory } from '@/types/category'

interface CategoriesStepProps {
  selectedIds: string[]
  onChange: (ids: string[]) => void
  customCategories: CustomCategory[]
  onCustomCategoriesChange: (categories: CustomCategory[]) => void
}

export interface CustomCategory {
  id: string
  display_name: string
  icon: string
  color: string
}

export function CategoriesStep({
  selectedIds,
  onChange,
  customCategories,
  onCustomCategoriesChange,
}: CategoriesStepProps) {
  const [defaults, setDefaults] = useState<DefaultCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newCategory, setNewCategory] = useState<Partial<CustomCategory>>({
    icon: 'circle',
    color: '#6B7280',
  })

  useEffect(() => {
    async function loadDefaults() {
      try {
        setLoading(true)
        const data = await categoryService.getDefaultCategories()
        setDefaults(data.defaults)
      } catch (err) {
        console.error('Error loading default categories:', err)
        setError('Failed to load categories')
      } finally {
        setLoading(false)
      }
    }
    loadDefaults()
  }, [])

  const toggleCategory = (categoryId: string) => {
    // Don't allow toggling OTHER - it's always included
    if (categoryId === 'OTHER') return

    if (selectedIds.includes(categoryId)) {
      onChange(selectedIds.filter((id) => id !== categoryId))
    } else {
      onChange([...selectedIds, categoryId])
    }
  }

  const handleAddCustom = () => {
    if (!newCategory.display_name?.trim()) return

    const customId = `CUSTOM_${Date.now()}`
    const custom: CustomCategory = {
      id: customId,
      display_name: newCategory.display_name.trim(),
      icon: newCategory.icon || 'circle',
      color: newCategory.color || '#6B7280',
    }

    onCustomCategoriesChange([...customCategories, custom])
    onChange([...selectedIds, customId])
    setNewCategory({ icon: 'circle', color: '#6B7280' })
    setShowAddForm(false)
  }

  const removeCustomCategory = (customId: string) => {
    onCustomCategoriesChange(customCategories.filter((c) => c.id !== customId))
    onChange(selectedIds.filter((id) => id !== customId))
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

  return (
    <div className="space-y-6">
      {/* Headline */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Choose Your Categories
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Select the categories you want to track
        </p>
        <button
          type="button"
          onClick={() => {
            const allDefaultIds = defaults
              .filter((d) => d.category_id !== 'OTHER')
              .map((d) => d.category_id)
            onChange(allDefaultIds)
          }}
          className={cn(
            'text-sm text-blue-600 dark:text-blue-400',
            'hover:text-blue-700 dark:hover:text-blue-300',
            'underline underline-offset-2',
            'transition-colors'
          )}
        >
          Use all defaults
        </button>
      </div>

      {/* Category grid */}
      <div className="grid grid-cols-2 gap-3 sm:max-h-[300px] overflow-y-auto pr-1">
        {defaults.map((category) => {
          const isOther = category.category_id === 'OTHER'
          const isSelected = selectedIds.includes(category.category_id) || isOther

          return (
            <button
              key={category.category_id}
              type="button"
              onClick={() => toggleCategory(category.category_id)}
              disabled={isOther}
              className={cn(
                'relative flex items-start gap-3 p-3 rounded-xl border-2 text-left transition-all',
                isOther
                  ? 'bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-800 cursor-not-allowed opacity-75'
                  : isSelected
                  ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500'
                  : 'bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
              )}
            >
              {/* Selection indicator */}
              {isSelected && !isOther && (
                <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                  <Check className="h-3 w-3 text-white" />
                </div>
              )}
              {isOther && (
                <div className="absolute top-2 right-2">
                  <Lock className="h-4 w-4 text-neutral-400" />
                </div>
              )}

              {/* Icon */}
              <div
                className="flex-shrink-0 p-2 rounded-lg"
                style={{ backgroundColor: `${category.color}20` }}
              >
                <DynamicIcon
                  name={category.icon}
                  className="h-5 w-5"
                  style={{ color: category.color }}
                />
              </div>

              {/* Text */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                  {category.display_name}
                </p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2">
                  {isOther ? 'Always included for misc.' : category.description}
                </p>
              </div>
            </button>
          )
        })}

        {/* Custom categories */}
        {customCategories.map((category) => (
          <div
            key={category.id}
            className={cn(
              'relative flex items-start gap-3 p-3 rounded-xl border-2 text-left',
              'bg-green-50 dark:bg-green-900/20 border-green-500'
            )}
          >
            {/* Remove button */}
            <button
              type="button"
              onClick={() => removeCustomCategory(category.id)}
              className="absolute top-2 right-2 p-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50"
            >
              <X className="h-3 w-3" />
            </button>

            {/* Icon */}
            <div
              className="flex-shrink-0 p-2 rounded-lg"
              style={{ backgroundColor: `${category.color}20` }}
            >
              <DynamicIcon
                name={category.icon}
                className="h-5 w-5"
                style={{ color: category.color }}
              />
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                {category.display_name}
              </p>
              <p className="text-xs text-green-600 dark:text-green-400">
                Custom category
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Add custom category */}
      {!showAddForm ? (
        <button
          type="button"
          onClick={() => setShowAddForm(true)}
          className={cn(
            'w-full flex items-center justify-center gap-2 p-3 rounded-xl border-2 border-dashed',
            'border-neutral-300 dark:border-neutral-700',
            'text-neutral-500 dark:text-neutral-400',
            'hover:border-neutral-400 dark:hover:border-neutral-600 hover:text-neutral-600 dark:hover:text-neutral-300',
            'transition-colors'
          )}
        >
          <Plus className="h-4 w-4" />
          Add Custom Category
        </button>
      ) : (
        <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              New Custom Category
            </h3>
            <button
              type="button"
              onClick={() => {
                setShowAddForm(false)
                setNewCategory({ icon: 'circle', color: '#6B7280' })
              }}
              className="p-1 rounded text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Name input */}
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Name
            </label>
            <input
              type="text"
              value={newCategory.display_name || ''}
              onChange={(e) =>
                setNewCategory({ ...newCategory, display_name: e.target.value })
              }
              placeholder="e.g., Subscriptions"
              className={cn(
                'w-full px-3 py-2 text-sm',
                'rounded-lg border',
                'bg-white dark:bg-neutral-800',
                'border-neutral-200 dark:border-neutral-700',
                'text-neutral-900 dark:text-neutral-100',
                'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
                'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
              )}
            />
          </div>

          {/* Icon picker */}
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Icon
            </label>
            <IconPicker
              value={newCategory.icon || 'circle'}
              onChange={(icon) => setNewCategory({ ...newCategory, icon })}
            />
          </div>

          {/* Color picker */}
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Color
            </label>
            <ColorPicker
              value={newCategory.color || '#6B7280'}
              onChange={(color) => setNewCategory({ ...newCategory, color })}
            />
          </div>

          {/* Add button */}
          <button
            type="button"
            onClick={handleAddCustom}
            disabled={!newCategory.display_name?.trim()}
            className={cn(
              'w-full px-4 py-2 text-sm font-medium rounded-lg',
              'bg-blue-600 text-white',
              'hover:bg-blue-700',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors'
            )}
          >
            Add Category
          </button>
        </div>
      )}

      {/* Selected count */}
      <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center">
        {selectedIds.length} categories selected (plus OTHER)
      </p>
    </div>
  )
}
