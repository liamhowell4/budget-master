import { useState, useEffect, useMemo } from 'react'
import { cn } from '@/utils/cn'
import { DynamicIcon } from '@/components/ui/IconPicker'
import { categoryService } from '@/services/categoryService'
import { Spinner } from '@/components/ui/Spinner'
import type { DefaultCategory } from '@/types/category'
import type { CustomCategory } from './CategoriesStep'

interface ExclusionsStepProps {
  selectedCategoryIds: string[]
  customCategories: CustomCategory[]
  excludedCategoryIds: string[]
  onChange: (excluded: string[]) => void
  onSkip: () => void
}

export function ExclusionsStep({
  selectedCategoryIds,
  customCategories,
  excludedCategoryIds,
  onChange,
  onSkip,
}: ExclusionsStepProps) {
  const [defaults, setDefaults] = useState<DefaultCategory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const data = await categoryService.getDefaultCategories()
        setDefaults(data.defaults)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Pre-check RENT and UTILITIES on first load if user selected them
  useEffect(() => {
    if (defaults.length === 0 || excludedCategoryIds.length > 0) return
    const preChecked = ['RENT', 'UTILITIES'].filter((id) =>
      selectedCategoryIds.includes(id)
    )
    if (preChecked.length > 0) onChange(preChecked)
  }, [defaults]) // eslint-disable-line react-hooks/exhaustive-deps

  const displayCategories = useMemo(() => {
    const selected = defaults.filter(
      (d) => selectedCategoryIds.includes(d.category_id) && d.category_id !== 'OTHER'
    )
    const custom = customCategories.map((c) => ({
      category_id: c.id,
      display_name: c.display_name,
      icon: c.icon,
      color: c.color,
      description: 'Custom category',
      is_system: false,
    }))
    return [...selected, ...custom]
  }, [defaults, selectedCategoryIds, customCategories])

  const toggle = (categoryId: string) => {
    if (excludedCategoryIds.includes(categoryId)) {
      onChange(excludedCategoryIds.filter((id) => id !== categoryId))
    } else {
      onChange([...excludedCategoryIds, categoryId])
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Exclude Fixed Costs?
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-sm mx-auto">
          Fixed costs like rent are hard to control month-to-month. Excluding them lets you focus your budget on spending you can actually adjust. Excluded categories still have their own caps — they just do not count toward your overall total.
        </p>
      </div>

      {displayCategories.length > 0 ? (
        <div className="space-y-2 sm:max-h-[300px] overflow-y-auto pr-1">
          {displayCategories.map((category) => {
            const isExcluded = excludedCategoryIds.includes(category.category_id)
            return (
              <button
                key={category.category_id}
                type="button"
                onClick={() => toggle(category.category_id)}
                className={cn(
                  'w-full flex items-center gap-3 p-3 rounded-xl border-2 text-left transition-all',
                  isExcluded
                    ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-500'
                    : 'bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
                )}
              >
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-lg flex-shrink-0 p-1.5"
                  style={{ backgroundColor: `${category.color}20` }}
                >
                  <DynamicIcon
                    name={category.icon}
                    className="h-4 w-4"
                    style={{ color: category.color }}
                  />
                </div>
                <span className="flex-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {category.display_name}
                </span>
                <div
                  className={cn(
                    'w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0',
                    isExcluded
                      ? 'bg-amber-500 border-amber-500'
                      : 'border-neutral-300 dark:border-neutral-600'
                  )}
                >
                  {isExcluded && (
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      ) : (
        <p className="text-center text-sm text-neutral-500 dark:text-neutral-400 py-4">
          No categories available to exclude.
        </p>
      )}

      <div className="text-center">
        <button
          type="button"
          onClick={() => {
            onChange([])
            onSkip()
          }}
          className="text-sm text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
        >
          Do not exclude anything
        </button>
      </div>
    </div>
  )
}
