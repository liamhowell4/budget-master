import { cn } from '@/utils/cn'
import { BUDGET_THRESHOLDS } from '@/utils/constants'

interface ProgressBarProps {
  percentage: number
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md'
}

export function ProgressBar({
  percentage,
  className,
  showLabel = false,
  size = 'md',
}: ProgressBarProps) {
  const clampedPercentage = Math.min(Math.max(percentage, 0), 100)

  const getBarColor = () => {
    if (percentage >= BUDGET_THRESHOLDS.DANGER) return 'bg-[var(--error)]'
    if (percentage >= BUDGET_THRESHOLDS.WARNING) return 'bg-[var(--warning)]'
    if (percentage >= BUDGET_THRESHOLDS.INFO) return 'bg-amber-400'
    return 'bg-[var(--success)]'
  }

  const heightClass = size === 'sm' ? 'h-1' : 'h-1.5'

  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn(
          'w-full rounded-full overflow-hidden',
          'bg-[var(--surface-secondary)]',
          heightClass
        )}
      >
        <div
          className={cn(
            'rounded-full transition-all duration-300 ease-out',
            heightClass,
            getBarColor()
          )}
          style={{ width: `${clampedPercentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="mt-1 text-xs text-[var(--text-muted)]">
          {percentage.toFixed(0)}%
        </span>
      )}
    </div>
  )
}
