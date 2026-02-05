import { useState, useEffect } from 'react'
import { cn } from '@/utils/cn'
import { Modal } from '@/components/ui/Modal'
import { IconPicker, DynamicIcon } from '@/components/ui/IconPicker'
import { ColorPicker } from '@/components/ui/ColorPicker'
import type { Category, CategoryCreate, CategoryUpdate } from '@/types/category'

interface CategoryModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: CategoryCreate | CategoryUpdate) => Promise<{ success: boolean; error?: string }>
  category?: Category | null // null for create, Category for edit
  availableBudget: number
  existingNames: string[] // For duplicate name validation
}

export function CategoryModal({
  isOpen,
  onClose,
  onSave,
  category,
  availableBudget,
  existingNames,
}: CategoryModalProps) {
  const isEditing = !!category
  const [displayName, setDisplayName] = useState('')
  const [icon, setIcon] = useState('circle')
  const [color, setColor] = useState('#3B82F6')
  const [monthlyCap, setMonthlyCap] = useState('')
  const [excludeFromTotal, setExcludeFromTotal] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<'details' | 'icon' | 'color'>('details')

  // Calculate max budget for this category
  const maxBudget = isEditing
    ? availableBudget + (category?.monthly_cap || 0)
    : availableBudget

  // Reset form when opening/closing or category changes
  useEffect(() => {
    if (isOpen) {
      if (category) {
        setDisplayName(category.display_name)
        setIcon(category.icon)
        setColor(category.color)
        setMonthlyCap(category.monthly_cap.toString())
        setExcludeFromTotal(category.exclude_from_total || false)
      } else {
        setDisplayName('')
        setIcon('circle')
        setColor('#3B82F6')
        setMonthlyCap('')
        setExcludeFromTotal(false)
      }
      setError(null)
      setActiveTab('details')
    }
  }, [isOpen, category])

  const validateForm = (): string | null => {
    const trimmedName = displayName.trim()

    if (!trimmedName) {
      return 'Name is required'
    }

    if (trimmedName.length > 30) {
      return 'Name must be 30 characters or less'
    }

    // Check for duplicate name (case-insensitive), excluding current category when editing
    const nameLower = trimmedName.toLowerCase()
    const duplicateExists = existingNames
      .filter((name) => !isEditing || name.toLowerCase() !== category?.display_name.toLowerCase())
      .some((name) => name.toLowerCase() === nameLower)

    if (duplicateExists) {
      return 'A category with this name already exists'
    }

    const cap = parseFloat(monthlyCap)
    if (isNaN(cap) || cap < 0) {
      return 'Budget must be a valid non-negative number'
    }

    if (cap > maxBudget) {
      return `Budget exceeds available amount ($${maxBudget.toFixed(2)})`
    }

    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setSaving(true)
    setError(null)

    try {
      const data: CategoryCreate | CategoryUpdate = isEditing
        ? {
            display_name: displayName.trim(),
            icon,
            color,
            monthly_cap: parseFloat(monthlyCap) || 0,
            exclude_from_total: excludeFromTotal,
          }
        : {
            display_name: displayName.trim(),
            icon,
            color,
            monthly_cap: parseFloat(monthlyCap) || 0,
          }

      const result = await onSave(data)

      if (result.success) {
        onClose()
      } else {
        setError(result.error || 'Failed to save category')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Category' : 'Create Category'}
      className="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Tab navigation */}
        <div className="flex border-b border-neutral-200 dark:border-neutral-700">
          {(['details', 'icon', 'color'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={cn(
                'flex-1 py-2 text-sm font-medium transition-colors',
                'border-b-2 -mb-px',
                activeTab === tab
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'
              )}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Details tab */}
        {activeTab === 'details' && (
          <div className="space-y-4">
            {/* Preview */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
              <div
                className="p-2 rounded-lg"
                style={{ backgroundColor: `${color}20` }}
              >
                <DynamicIcon name={icon} className="h-5 w-5" style={{ color }} />
              </div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {displayName || 'Category Name'}
              </span>
            </div>

            {/* Name input */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g., Pet Supplies"
                maxLength={30}
                className={cn(
                  'w-full px-3 py-2 text-sm',
                  'rounded-lg border',
                  'bg-white dark:bg-neutral-900',
                  'border-neutral-200 dark:border-neutral-700',
                  'text-neutral-900 dark:text-neutral-100',
                  'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
                )}
              />
              <p className="mt-1 text-xs text-neutral-500">{displayName.length}/30 characters</p>
            </div>

            {/* Budget input */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Monthly Budget
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">$</span>
                <input
                  type="number"
                  value={monthlyCap}
                  onChange={(e) => setMonthlyCap(e.target.value)}
                  placeholder="0.00"
                  min="0"
                  step="0.01"
                  className={cn(
                    'w-full pl-7 pr-3 py-2 text-sm',
                    'rounded-lg border',
                    'bg-white dark:bg-neutral-900',
                    'border-neutral-200 dark:border-neutral-700',
                    'text-neutral-900 dark:text-neutral-100',
                    'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
                  )}
                />
              </div>
              <p className="mt-1 text-xs text-neutral-500">
                Available: ${maxBudget.toFixed(2)}
              </p>
            </div>

            {/* Exclude from total checkbox - only show when editing */}
            {isEditing && (
              <div className="pt-2 border-t border-neutral-200 dark:border-neutral-700">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={excludeFromTotal}
                    onChange={(e) => setExcludeFromTotal(e.target.checked)}
                    className={cn(
                      'mt-0.5 h-4 w-4 rounded',
                      'border-neutral-300 dark:border-neutral-600',
                      'text-amber-500 focus:ring-amber-500/20',
                      'bg-white dark:bg-neutral-900'
                    )}
                  />
                  <div>
                    <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100 group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                      Exclude from total budget
                    </span>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                      Spending in this category won't count toward your overall monthly budget total.
                    </p>
                  </div>
                </label>
              </div>
            )}
          </div>
        )}

        {/* Icon tab */}
        {activeTab === 'icon' && (
          <IconPicker value={icon} onChange={setIcon} />
        )}

        {/* Color tab */}
        {activeTab === 'color' && (
          <ColorPicker value={color} onChange={setColor} />
        )}

        {/* Error message */}
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        {/* Action buttons */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
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
            type="submit"
            disabled={saving}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              'bg-blue-600 text-white',
              'hover:bg-blue-700',
              'disabled:opacity-50'
            )}
          >
            {saving ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Category'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
