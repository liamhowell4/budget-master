import { useState, useEffect, useMemo } from 'react'
import { cn } from '@/utils/cn'
import { DynamicIcon } from '@/components/ui/IconPicker'
import { Lock } from 'lucide-react'
import { categoryService } from '@/services/categoryService'
import { Spinner } from '@/components/ui/Spinner'
import type { DefaultCategory } from '@/types/category'
import type { CustomCategory } from './CategoriesStep'

interface CapsStepProps {
  totalBudget: number
  selectedCategoryIds: string[]
  customCategories: CustomCategory[]
  caps: Record<string, number>
  onChange: (caps: Record<string, number>) => void
}

export function CapsStep({
  totalBudget,
  selectedCategoryIds,
  customCategories,
  caps,
  onChange,
}: CapsStepProps) {
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

  // Get categories to display (selected defaults + custom, excluding OTHER)
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

  // Calculate totals
  const allocatedTotal = useMemo(() => {
    return Object.values(caps).reduce((sum, cap) => sum + cap, 0)
  }, [caps])

  const remaining = totalBudget - allocatedTotal
  const isOverBudget = remaining < 0

  const handleCapChange = (categoryId: string, value: number) => {
    onChange({
      ...caps,
      [categoryId]: Math.max(0, value),
    })
  }

  const handleSliderChange = (categoryId: string, percentage: number) => {
    const value = Math.round((percentage / 100) * totalBudget)
    handleCapChange(categoryId, value)
  }

  const handleInputChange = (categoryId: string, inputValue: string) => {
    const value = parseFloat(inputValue.replace(/[^0-9.]/g, '')) || 0
    handleCapChange(categoryId, value)
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
      {/* Headline */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Allocate Your Budget
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Set spending limits for each category
        </p>
      </div>

      {/* Budget summary */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-800">
        <div className="text-sm">
          <p className="text-neutral-500 dark:text-neutral-400">
            Total Budget
          </p>
          <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            ${totalBudget.toLocaleString()}
          </p>
        </div>
        <div className="text-sm text-right">
          <p className="text-neutral-500 dark:text-neutral-400">
            {isOverBudget ? 'Over by' : 'Remaining'}
          </p>
          <p
            className={cn(
              'text-lg font-semibold',
              isOverBudget
                ? 'text-red-600 dark:text-red-400'
                : 'text-green-600 dark:text-green-400'
            )}
          >
            ${Math.abs(remaining).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Warning if over budget */}
      {isOverBudget && (
        <p className="text-sm text-red-600 dark:text-red-400 text-center">
          Category allocations exceed your total budget. Please reduce some caps.
        </p>
      )}

      {/* Category sliders */}
      <div className="space-y-4 sm:max-h-[280px] overflow-y-auto pr-1">
        {displayCategories.map((category) => {
          const cap = caps[category.category_id] || 0
          const percentage = totalBudget > 0 ? (cap / totalBudget) * 100 : 0

          return (
            <div key={category.category_id} className="space-y-2">
              {/* Category header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="p-1.5 rounded-lg"
                    style={{ backgroundColor: `${category.color}20` }}
                  >
                    <DynamicIcon
                      name={category.icon}
                      className="h-4 w-4"
                      style={{ color: category.color }}
                    />
                  </div>
                  <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    {category.display_name}
                  </span>
                </div>

                {/* Value input */}
                <div className="relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-sm text-neutral-400">
                    $
                  </span>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={cap > 0 ? cap.toLocaleString() : ''}
                    onChange={(e) =>
                      handleInputChange(category.category_id, e.target.value)
                    }
                    placeholder="0"
                    className={cn(
                      'w-24 pl-5 pr-2 py-1 text-sm text-right',
                      'rounded-lg border',
                      'bg-white dark:bg-neutral-800',
                      'border-neutral-200 dark:border-neutral-700',
                      'text-neutral-900 dark:text-neutral-100',
                      'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
                    )}
                  />
                </div>
              </div>

              {/* Slider */}
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={percentage}
                  onChange={(e) =>
                    handleSliderChange(category.category_id, parseFloat(e.target.value))
                  }
                  className="flex-1 h-2 rounded-full appearance-none cursor-pointer
                    bg-neutral-200 dark:bg-neutral-700
                    [&::-webkit-slider-thumb]:appearance-none
                    [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-blue-500
                    [&::-webkit-slider-thumb]:cursor-pointer
                    [&::-webkit-slider-thumb]:transition-transform
                    [&::-webkit-slider-thumb]:hover:scale-110
                    [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4
                    [&::-moz-range-thumb]:rounded-full
                    [&::-moz-range-thumb]:bg-blue-500
                    [&::-moz-range-thumb]:border-0
                    [&::-moz-range-thumb]:cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, ${category.color} 0%, ${category.color} ${percentage}%, rgb(229 231 235) ${percentage}%, rgb(229 231 235) 100%)`,
                  }}
                />
                <span className="text-xs text-neutral-500 dark:text-neutral-400 w-10 text-right">
                  {percentage.toFixed(0)}%
                </span>
              </div>
            </div>
          )
        })}

        {/* OTHER category (read-only) */}
        <div className="space-y-2 opacity-75">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-neutral-200 dark:bg-neutral-700">
                <DynamicIcon
                  name="more-horizontal"
                  className="h-4 w-4 text-neutral-500"
                />
              </div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Other
              </span>
              <Lock className="h-3 w-3 text-neutral-400" />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-neutral-500 dark:text-neutral-400">
                ${Math.max(0, remaining).toLocaleString()}
              </span>
              <span className="text-xs text-neutral-400">(auto)</span>
            </div>
          </div>

          {/* Info text */}
          <p className="text-xs text-neutral-500 dark:text-neutral-400 pl-8">
            Unallocated budget goes here automatically
          </p>
        </div>
      </div>
    </div>
  )
}
