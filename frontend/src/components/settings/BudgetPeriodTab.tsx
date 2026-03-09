import { useState, useEffect } from 'react'
import { cn } from '@/utils/cn'
import { Check, Loader2, AlertCircle, Info } from 'lucide-react'
import { getUserSettings, updateUserSettings } from '@/services/userSettingsService'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import type { BudgetPeriodType } from '@/components/onboarding/BudgetPeriodStep'
import { BudgetPeriodStep } from '@/components/onboarding/BudgetPeriodStep'

export function BudgetPeriodTab() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [periodType, setPeriodType] = useState<BudgetPeriodType>('monthly')
  const [monthStartDay, setMonthStartDay] = useState(1)
  const [weekStartDay, setWeekStartDay] = useState("Monday")
  const [biweeklyAnchor, setBiweeklyAnchor] = useState(() => new Date().toISOString().split('T')[0])

  useEffect(() => {
    let cancelled = false

    async function fetchSettings() {
      try {
        const settings = await getUserSettings()
        if (!cancelled) {
          setPeriodType((settings.budget_period_type as BudgetPeriodType) ?? 'monthly')
          setMonthStartDay(settings.budget_month_start_day ?? 1)
          setWeekStartDay(settings.budget_week_start_day ?? "Monday")
          setBiweeklyAnchor(settings.budget_biweekly_anchor ?? new Date().toISOString().split('T')[0])
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load budget period settings.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchSettings()
    return () => {
      cancelled = true
    }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSaveSuccess(false)

    try {
      await updateUserSettings({
        budget_period_type: periodType,
        budget_month_start_day: monthStartDay,
        budget_week_start_day: weekStartDay,
        budget_biweekly_anchor: biweeklyAnchor,
      })
      // Invalidate budget cache so dashboard refetches with new period settings
      invalidateBudgetCache()
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch {
      setError('Failed to save budget period settings. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium text-[var(--text-primary)] mb-1">
          Budget Period
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          Choose how your budget is split and tracked over time
        </p>
      </div>

      {/* Info callout */}
      <div className={cn(
        'flex items-start gap-3 p-3 rounded-lg',
        'bg-blue-50 dark:bg-blue-900/20',
        'border border-blue-200 dark:border-blue-800'
      )}>
        <Info className="h-4 w-4 text-blue-500 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-blue-700 dark:text-blue-300">
          Changing your period only changes how your budget is tracked. Your monthly caps stay the same.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" />
        </div>
      ) : (
        <div className="space-y-6">
          <BudgetPeriodStep
            periodType={periodType}
            monthStartDay={monthStartDay}
            weekStartDay={weekStartDay}
            biweeklyAnchor={biweeklyAnchor}
            onPeriodTypeChange={setPeriodType}
            onMonthStartDayChange={setMonthStartDay}
            onWeekStartDayChange={setWeekStartDay}
            onBiweeklyAnchorChange={setBiweeklyAnchor}
          />

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-500">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                'bg-[var(--accent-primary)] text-white',
                'hover:bg-[var(--accent-hover)]',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : saveSuccess ? (
                <Check className="h-4 w-4" />
              ) : null}
              {saving ? 'Saving...' : saveSuccess ? 'Saved' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
