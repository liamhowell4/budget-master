import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/formatters'
import { formatDateRange } from './cardUtils'
import type { ToolDate } from './cardUtils'

interface SpendingSummaryResult {
  total: number
  count: number
  average_per_transaction: number
  start_date: ToolDate
  end_date: ToolDate
}

export function isSpendingSummaryResult(result: unknown): result is SpendingSummaryResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'total' in result &&
    'count' in result &&
    'average_per_transaction' in result &&
    'start_date' in result &&
    'end_date' in result
  )
}

interface SpendingSummaryCardProps {
  result: SpendingSummaryResult
}

export function SpendingSummaryCard({ result }: SpendingSummaryCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl p-4 max-w-sm',
        'border border-neutral-200/50 dark:border-neutral-700/50',
        'bg-neutral-50 dark:bg-neutral-800/60'
      )}
    >
      <div className="mb-3">
        <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          Spending Summary
        </h3>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          {formatDateRange(result.start_date, result.end_date)}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Total</p>
          <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
            {formatCurrency(result.total)}
          </p>
        </div>
        <div>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Count</p>
          <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
            {result.count}
          </p>
        </div>
        <div>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Avg/Expense</p>
          <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
            {formatCurrency(result.average_per_transaction)}
          </p>
        </div>
      </div>
    </div>
  )
}
