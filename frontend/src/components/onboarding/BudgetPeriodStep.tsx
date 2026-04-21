import { cn } from '@/utils/cn'
import { Calendar } from 'lucide-react'

interface BudgetPeriodStepProps {
  monthStartDay: number | 'last'
  onMonthStartDayChange: (value: number | 'last') => void
}

type StartDayMode = 'first' | 'last' | 'specific'

function inferMode(value: number | 'last'): StartDayMode {
  if (value === 'last') return 'last'
  if (value === 1) return 'first'
  return 'specific'
}

export function BudgetPeriodStep({
  monthStartDay,
  onMonthStartDayChange,
}: BudgetPeriodStepProps) {
  const mode = inferMode(monthStartDay)

  const handleModeChange = (newMode: StartDayMode) => {
    if (newMode === 'first') {
      onMonthStartDayChange(1)
    } else if (newMode === 'last') {
      onMonthStartDayChange('last')
    } else {
      // Switching to Specific: use current value if it's already a specific int, else 15
      const defaultDay = typeof monthStartDay === 'number' && monthStartDay !== 1 ? monthStartDay : 15
      onMonthStartDayChange(defaultDay)
    }
  }

  const segments: { mode: StartDayMode; label: string }[] = [
    { mode: 'first', label: 'First' },
    { mode: 'last', label: 'Last' },
    { mode: 'specific', label: 'Specific' },
  ]

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Budget Period
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-sm mx-auto">
          Pick which day of the month your budget period starts. You can always change this later in Settings.
        </p>
      </div>

      {/* Icon */}
      <div className="flex justify-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-800/40">
          <Calendar className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
      </div>

      {/* Three-segment control */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 text-center">
          What day does your budget month start?
        </label>
        <div
          className={cn(
            'flex rounded-xl border overflow-hidden',
            'border-neutral-200 dark:border-neutral-700',
            'bg-neutral-100 dark:bg-neutral-800'
          )}
          role="group"
          aria-label="Budget month start day"
        >
          {segments.map(({ mode: segMode, label }) => {
            const isActive = mode === segMode
            return (
              <button
                key={segMode}
                type="button"
                onClick={() => handleModeChange(segMode)}
                aria-pressed={isActive}
                className={cn(
                  'flex-1 py-2.5 text-sm font-medium transition-all',
                  isActive
                    ? 'bg-white dark:bg-neutral-900 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
                )}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Specific number input */}
      {mode === 'specific' && (
        <div className="space-y-2 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
          <label
            htmlFor="specific-day-input"
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300"
          >
            Day of month (1–28)
          </label>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Max 28 so it works in every month. Align with your pay day.
          </p>
          <input
            id="specific-day-input"
            type="number"
            min={1}
            max={28}
            value={typeof monthStartDay === 'number' ? monthStartDay : 15}
            onChange={(e) => {
              const val = Math.max(1, Math.min(28, parseInt(e.target.value) || 1))
              onMonthStartDayChange(val)
            }}
            className={cn(
              'w-24 px-3 py-2 rounded-lg border',
              'bg-white dark:bg-neutral-900',
              'border-neutral-200 dark:border-neutral-700',
              'text-sm text-neutral-900 dark:text-neutral-100',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            )}
          />
        </div>
      )}

      {/* Summary text */}
      <p className="text-xs text-center text-neutral-400 dark:text-neutral-500">
        {mode === 'first' && 'Your budget period will start on the 1st of each month.'}
        {mode === 'last' && 'Your budget period will start on the last day of each month.'}
        {mode === 'specific' &&
          typeof monthStartDay === 'number' &&
          `Your budget period will start on day ${monthStartDay} of each month.`}
      </p>
    </div>
  )
}
