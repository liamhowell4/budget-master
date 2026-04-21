import { useState, useEffect } from 'react'
import { cn } from '@/utils/cn'
import { Check, Loader2, AlertCircle, Info } from 'lucide-react'
import { getUserSettings, updateUserSettings } from '@/services/userSettingsService'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import { BudgetPeriodStep } from '@/components/onboarding/BudgetPeriodStep'

export function BudgetPeriodTab() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [monthStartDay, setMonthStartDay] = useState<number | 'last'>(1)

  useEffect(() => {
    let cancelled = false

    async function fetchSettings() {
      try {
        const settings = await getUserSettings()
        if (!cancelled) {
          setMonthStartDay(settings.budget_month_start_day ?? 1)
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
        budget_month_start_day: monthStartDay,
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
          Choose which day of the month your budget period starts
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
          Your budget runs monthly. Pick which day of the month it starts — this does not affect your monthly caps.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" />
        </div>
      ) : (
        <div className="space-y-6">
          <BudgetPeriodStep
            monthStartDay={monthStartDay}
            onMonthStartDayChange={setMonthStartDay}
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
