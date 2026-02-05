import { useState, useEffect, useMemo } from 'react'
import { cn } from '@/utils/cn'
import { DynamicIcon } from '@/components/ui/IconPicker'
import { DollarSign, Grid3X3, PieChart, Check } from 'lucide-react'
import { categoryService } from '@/services/categoryService'
import { Spinner } from '@/components/ui/Spinner'
import type { DefaultCategory } from '@/types/category'
import type { CustomCategory } from './CategoriesStep'

interface ReviewStepProps {
  totalBudget: number
  selectedCategoryIds: string[]
  customCategories: CustomCategory[]
  caps: Record<string, number>
}

export function ReviewStep({
  totalBudget,
  selectedCategoryIds,
  customCategories,
  caps,
}: ReviewStepProps) {
  const [defaults, setDefaults] = useState<DefaultCategory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDefaults() {
      try {
        setLoading(true)
        const data = await categoryService.getDefaultCategories()
        setDefaults(data.defaults)
      } finally {
        setLoading(false)
      }
    }
    loadDefaults()
  }, [])

  // Get selected categories with their details
  const selectedCategories = useMemo(() => {
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
      isCustom: true,
    }))
    return [...selected, ...custom]
  }, [defaults, selectedCategoryIds, customCategories])

  // Calculate totals
  const allocatedTotal = useMemo(() => {
    return Object.values(caps).reduce((sum, cap) => sum + cap, 0)
  }, [caps])

  const unallocated = totalBudget - allocatedTotal

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Headline */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Review Your Setup
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Confirm your budget settings before completing
        </p>
      </div>

      {/* Scrollable review content */}
      <div className="space-y-4 sm:max-h-[320px] overflow-y-auto pr-1">
        {/* Total Budget Section */}
        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/40">
              <DollarSign className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400">Monthly Budget</p>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                ${totalBudget.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Categories Section */}
        <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 mb-3">
            <Grid3X3 className="h-4 w-4 text-neutral-500" />
            <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Categories ({selectedCategories.length + 1} total)
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedCategories.map((cat) => (
              <div
                key={cat.category_id}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm',
                  'bg-white dark:bg-neutral-800',
                  'border border-neutral-200 dark:border-neutral-700'
                )}
              >
                <DynamicIcon
                  name={cat.icon}
                  className="h-3.5 w-3.5"
                  style={{ color: cat.color }}
                />
                <span className="text-neutral-700 dark:text-neutral-300">
                  {cat.display_name}
                </span>
              </div>
            ))}
            {/* OTHER is always included */}
            <div
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm',
                'bg-neutral-100 dark:bg-neutral-800',
                'border border-neutral-200 dark:border-neutral-700'
              )}
            >
              <DynamicIcon
                name="more-horizontal"
                className="h-3.5 w-3.5 text-neutral-500"
              />
              <span className="text-neutral-500 dark:text-neutral-400">Other</span>
            </div>
          </div>
        </div>

        {/* Budget Allocations Section */}
        <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 mb-3">
            <PieChart className="h-4 w-4 text-neutral-500" />
            <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Budget Allocations
            </p>
          </div>
          <div className="space-y-2">
            {selectedCategories.map((cat) => {
              const cap = caps[cat.category_id] || 0
              if (cap === 0) return null
              const percentage = ((cap / totalBudget) * 100).toFixed(0)
              return (
                <div
                  key={cat.category_id}
                  className="flex items-center justify-between py-1.5"
                >
                  <div className="flex items-center gap-2">
                    <DynamicIcon
                      name={cat.icon}
                      className="h-4 w-4"
                      style={{ color: cat.color }}
                    />
                    <span className="text-sm text-neutral-700 dark:text-neutral-300">
                      {cat.display_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      ${cap.toLocaleString()}
                    </span>
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">
                      ({percentage}%)
                    </span>
                  </div>
                </div>
              )
            })}
            {/* Unallocated / Other */}
            {unallocated > 0 && (
              <div className="flex items-center justify-between py-1.5 border-t border-neutral-200 dark:border-neutral-700 mt-2 pt-2">
                <div className="flex items-center gap-2">
                  <DynamicIcon
                    name="more-horizontal"
                    className="h-4 w-4 text-neutral-500"
                  />
                  <span className="text-sm text-neutral-500 dark:text-neutral-400">
                    Other (unallocated)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                    ${unallocated.toLocaleString()}
                  </span>
                  <span className="text-xs text-neutral-400">
                    ({((unallocated / totalBudget) * 100).toFixed(0)}%)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Ready message */}
        <div className="flex items-center justify-center gap-2 py-2 text-green-600 dark:text-green-400">
          <Check className="h-4 w-4" />
          <span className="text-sm font-medium">Ready to complete setup</span>
        </div>
      </div>
    </div>
  )
}
