import { useMemo } from 'react'
import { cn } from '@/utils/cn'
import { Calendar, CalendarDays, CalendarRange } from 'lucide-react'

export type BudgetPeriodType = 'monthly' | 'weekly' | 'biweekly'

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function getNextTwoWeeksDates(): { label: string; value: string }[] {
  const dates: { label: string; value: string }[] = []
  const now = new Date()
  for (let i = 0; i < 14; i++) {
    const d = new Date(now)
    d.setDate(now.getDate() + i)
    const iso = d.toISOString().split('T')[0]
    const label = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    dates.push({ label, value: iso })
  }
  return dates
}

interface BudgetPeriodStepProps {
  periodType: BudgetPeriodType
  monthStartDay: number
  weekStartDay: string
  biweeklyAnchor: string
  onPeriodTypeChange: (type: BudgetPeriodType) => void
  onMonthStartDayChange: (day: number) => void
  onWeekStartDayChange: (day: string) => void
  onBiweeklyAnchorChange: (date: string) => void
}

interface PeriodOption {
  type: BudgetPeriodType
  label: string
  description: string
  icon: typeof Calendar
}

const PERIOD_OPTIONS: PeriodOption[] = [
  {
    type: 'monthly',
    label: 'Monthly',
    description: 'Track spending over a calendar-style month.',
    icon: Calendar,
  },
  {
    type: 'weekly',
    label: 'Weekly',
    description: 'Your monthly budget will be automatically split into weekly windows.',
    icon: CalendarDays,
  },
  {
    type: 'biweekly',
    label: 'Biweekly',
    description: 'Your monthly budget will be automatically split into biweekly windows.',
    icon: CalendarRange,
  },
]

export function BudgetPeriodStep({
  periodType,
  monthStartDay,
  weekStartDay,
  biweeklyAnchor,
  onPeriodTypeChange,
  onMonthStartDayChange,
  onWeekStartDayChange,
  onBiweeklyAnchorChange,
}: BudgetPeriodStepProps) {
  const biweeklyOptions = useMemo(() => {
    const list = getNextTwoWeeksDates()
    if (biweeklyAnchor && !list.some((d) => d.value === biweeklyAnchor)) {
      const savedDate = new Date(biweeklyAnchor + 'T00:00:00')
      const label =
        savedDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) +
        ' (saved)'
      return [{ label, value: biweeklyAnchor }, ...list]
    }
    return list
  }, [biweeklyAnchor])

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Budget Period
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-sm mx-auto">
          How would you like to track your spending? You can always change this later in Settings.
        </p>
      </div>

      {/* Period type radio cards */}
      <div className="space-y-2">
        {PERIOD_OPTIONS.map((option) => {
          const Icon = option.icon
          const isSelected = periodType === option.type
          return (
            <button
              key={option.type}
              type="button"
              onClick={() => onPeriodTypeChange(option.type)}
              className={cn(
                'w-full flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all',
                isSelected
                  ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500'
                  : 'bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
              )}
              aria-pressed={isSelected}
            >
              <div
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-lg flex-shrink-0 mt-0.5',
                  isSelected
                    ? 'bg-blue-100 dark:bg-blue-800/40'
                    : 'bg-neutral-100 dark:bg-neutral-800'
                )}
              >
                <Icon
                  className={cn(
                    'h-5 w-5',
                    isSelected
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-neutral-500 dark:text-neutral-400'
                  )}
                />
              </div>
              <div className="flex-1 min-w-0">
                <p className={cn(
                  'text-sm font-semibold',
                  isSelected
                    ? 'text-blue-700 dark:text-blue-300'
                    : 'text-neutral-900 dark:text-neutral-100'
                )}>
                  {option.label}
                </p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                  {option.description}
                </p>
              </div>
              <div
                className={cn(
                  'w-4 h-4 rounded-full border-2 flex-shrink-0 mt-1 flex items-center justify-center',
                  isSelected
                    ? 'border-blue-500 bg-blue-500'
                    : 'border-neutral-300 dark:border-neutral-600'
                )}
              >
                {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
            </button>
          )
        })}
      </div>

      {/* Conditional sub-options */}
      {periodType === 'monthly' && (
        <div className="space-y-2 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            What day does your budget month start?
          </label>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Align with your pay day.
          </p>
          <input
            type="number"
            min={1}
            max={28}
            value={monthStartDay}
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
          <p className="text-xs text-neutral-400 dark:text-neutral-500">
            Day 1–28 (max 28 to work every month)
          </p>
        </div>
      )}

      {periodType === 'weekly' && (
        <div className="space-y-2 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            What day does your week start?
          </label>
          <div className="flex flex-wrap gap-2 pt-1">
            {DAY_NAMES.map((day) => {
              const isSelected = weekStartDay === day
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => onWeekStartDayChange(day)}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                    isSelected
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 ring-2 ring-blue-500'
                      : 'bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                  )}
                  aria-pressed={isSelected}
                >
                  {day.slice(0, 3)}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {periodType === 'biweekly' && (
        <div className="space-y-2 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            When does your next pay period start?
          </label>
          <select
            value={biweeklyAnchor}
            onChange={(e) => onBiweeklyAnchorChange(e.target.value)}
            className={cn(
              'w-full px-3 py-2 rounded-lg border appearance-none',
              'bg-white dark:bg-neutral-900',
              'border-neutral-200 dark:border-neutral-700',
              'text-sm text-neutral-900 dark:text-neutral-100',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            )}
          >
            {biweeklyOptions.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-neutral-400 dark:text-neutral-500">
            Future pay periods will repeat every 14 days from this date.
          </p>
        </div>
      )}
    </div>
  )
}
