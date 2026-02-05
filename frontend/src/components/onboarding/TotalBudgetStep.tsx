import { cn } from '@/utils/cn'

interface TotalBudgetStepProps {
  value: number
  onChange: (value: number) => void
  error?: string
}

const quickAmounts = [1500, 2000, 3000, 5000]

export function TotalBudgetStep({ value, onChange, error }: TotalBudgetStepProps) {
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value.replace(/[^0-9.]/g, '')
    const numValue = parseFloat(rawValue) || 0
    onChange(numValue)
  }

  const formatDisplayValue = (num: number): string => {
    if (num === 0) return ''
    return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
  }

  return (
    <div className="space-y-6">
      {/* Headline */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Set Your Monthly Budget
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          How much do you want to spend each month?
        </p>
      </div>

      {/* Large input */}
      <div className="flex justify-center">
        <div className="relative inline-block">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-3xl text-neutral-400 dark:text-neutral-500">
            $
          </span>
          <input
            type="text"
            inputMode="decimal"
            value={formatDisplayValue(value)}
            onChange={handleInputChange}
            placeholder="0"
            className={cn(
              'w-48 pl-10 pr-4 py-4 text-3xl font-semibold text-center',
              'rounded-xl border-2',
              'bg-white dark:bg-neutral-900',
              error
                ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                : 'border-neutral-200 dark:border-neutral-700 focus:border-blue-500 focus:ring-blue-500/20',
              'text-neutral-900 dark:text-neutral-100',
              'placeholder:text-neutral-300 dark:placeholder:text-neutral-600',
              'focus:outline-none focus:ring-2'
            )}
            autoFocus
          />
        </div>
      </div>

      {/* Error message */}
      {error && (
        <p className="text-center text-sm text-red-500 dark:text-red-400">
          {error}
        </p>
      )}

      {/* Quick select chips */}
      <div className="space-y-2">
        <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center">
          Quick select
        </p>
        <div className="flex justify-center flex-wrap gap-2">
          {quickAmounts.map((amount) => (
            <button
              key={amount}
              type="button"
              onClick={() => onChange(amount)}
              className={cn(
                'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                value === amount
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 ring-2 ring-blue-500'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
              )}
            >
              ${amount.toLocaleString()}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
