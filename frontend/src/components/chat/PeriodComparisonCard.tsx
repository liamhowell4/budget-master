import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/utils/cn'
import { formatCurrency, formatPercentage } from '@/utils/formatters'
import { CATEGORY_LABELS } from '@/utils/constants'
import { formatDateRange } from './cardUtils'
import type { ToolDate } from './cardUtils'
import type { ExpenseType } from '@/types/expense'

interface PeriodData {
  start: ToolDate
  end: ToolDate
  total: number
  count: number
}

interface ComparePeriodsResult {
  period1: PeriodData
  period2: PeriodData
  comparison: {
    difference: number
    percentage_change: number
  }
  category?: string
}

export function isComparePeriodsResult(result: unknown): result is ComparePeriodsResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'period1' in result &&
    'period2' in result &&
    'comparison' in result
  )
}

interface PeriodComparisonCardProps {
  result: ComparePeriodsResult
}

export function PeriodComparisonCard({ result }: PeriodComparisonCardProps) {
  const { period1, period2, comparison } = result
  const increased = comparison.difference > 0
  const noChange = comparison.difference === 0

  const categoryLabel = result.category
    ? CATEGORY_LABELS[result.category as ExpenseType] ?? result.category
    : null

  return (
    <div
      className={cn(
        'rounded-xl p-4 max-w-sm',
        'border border-neutral-200/50 dark:border-neutral-700/50',
        'bg-neutral-50 dark:bg-neutral-800/60'
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          Period Comparison
        </h3>
        {categoryLabel && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-neutral-200/60 dark:bg-neutral-700/60 text-neutral-600 dark:text-neutral-300">
            {categoryLabel}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="rounded-lg bg-white/60 dark:bg-neutral-900/40 p-2.5">
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            {formatDateRange(period1.start, period1.end)}
          </p>
          <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
            {formatCurrency(period1.total)}
          </p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 tabular-nums">
            {period1.count} expenses
          </p>
        </div>
        <div className="rounded-lg bg-white/60 dark:bg-neutral-900/40 p-2.5">
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            {formatDateRange(period2.start, period2.end)}
          </p>
          <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
            {formatCurrency(period2.total)}
          </p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 tabular-nums">
            {period2.count} expenses
          </p>
        </div>
      </div>

      {/* Delta indicator */}
      <div
        className={cn(
          'flex items-center gap-2 rounded-lg px-3 py-2',
          noChange && 'bg-neutral-100 dark:bg-neutral-800',
          increased && 'bg-red-50 dark:bg-red-950/30',
          !increased && !noChange && 'bg-emerald-50 dark:bg-emerald-950/30'
        )}
      >
        {!noChange &&
          (increased ? (
            <TrendingUp className="h-4 w-4 text-red-500 dark:text-red-400" />
          ) : (
            <TrendingDown className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
          ))}
        <span
          className={cn(
            'text-sm font-medium tabular-nums',
            noChange && 'text-neutral-600 dark:text-neutral-400',
            increased && 'text-red-600 dark:text-red-400',
            !increased && !noChange && 'text-emerald-600 dark:text-emerald-400'
          )}
        >
          {noChange
            ? 'No change'
            : `${increased ? '+' : ''}${formatCurrency(comparison.difference)} (${increased ? '+' : ''}${formatPercentage(comparison.percentage_change)})`}
        </span>
      </div>
    </div>
  )
}
