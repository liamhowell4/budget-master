import { useState } from 'react'
import { cn } from '@/utils/cn'
import { Lock, CreditCard, Calculator, ChevronRight, PenLine } from 'lucide-react'
import {
  calculateBudget,
  US_STATES,
  STATE_TAX_RATES,
  type PayFrequency,
  type DirectDepositInput,
  type SalaryInput,
  type BudgetCalculationResult,
} from '@/utils/budgetCalculator'

type Mode = 'direct' | 'salary'
type Screen = 'modeSelect' | 'incomeInput' | 'savingsRate' | 'result'

interface IncomePlannerStepProps {
  onApply: (monthlyBudget: number) => void
  onSkip: () => void
}

const FREQUENCY_LABELS: Record<PayFrequency, string> = {
  weekly: 'Weekly',
  biweekly: 'Every 2 weeks',
  semimonthly: 'Twice a month',
  monthly: 'Monthly',
}

function formatCurrency(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
}

function PrivacyNote() {
  return (
    <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-800 rounded-lg px-3 py-2">
      <Lock className="h-3.5 w-3.5 flex-shrink-0" />
      <span>None of this information is saved — it is used only to calculate your recommendation.</span>
    </div>
  )
}

export function IncomePlannerStep({ onApply, onSkip }: IncomePlannerStepProps) {
  const [screen, setScreen] = useState<Screen>('modeSelect')
  const [mode, setMode] = useState<Mode>('direct')

  // Direct deposit state
  const [takeHome, setTakeHome] = useState('')
  const [frequency, setFrequency] = useState<PayFrequency>('biweekly')

  // Salary state
  const [grossAnnual, setGrossAnnual] = useState('')
  const [selectedState, setSelectedState] = useState('TX')
  const [retirement401kPct, setRetirement401kPct] = useState('6')
  const [monthlyHealthcare, setMonthlyHealthcare] = useState('200')

  // Shared
  const [savingsRate, setSavingsRate] = useState(20)
  const [result, setResult] = useState<BudgetCalculationResult | null>(null)

  const handleModeSelect = (selected: Mode) => {
    setMode(selected)
    setScreen('incomeInput')
  }

  const handleIncomeNext = () => {
    setScreen('savingsRate')
  }

  const handleSavingsNext = () => {
    let input: DirectDepositInput | SalaryInput
    if (mode === 'direct') {
      input = {
        mode: 'direct',
        takeHome: parseFloat(takeHome.replace(/[^0-9.]/g, '')) || 0,
        frequency,
        savingsRate,
      }
    } else {
      input = {
        mode: 'salary',
        grossAnnual: parseFloat(grossAnnual.replace(/[^0-9.]/g, '')) || 0,
        state: selectedState,
        retirement401kPct: parseFloat(retirement401kPct) || 0,
        monthlyHealthcare: parseFloat(monthlyHealthcare.replace(/[^0-9.]/g, '')) || 0,
        savingsRate,
      }
    }
    const calc = calculateBudget(input)
    setResult(calc)
    setScreen('result')
  }

  const canProceedFromIncome = () => {
    if (mode === 'direct') {
      const val = parseFloat(takeHome.replace(/[^0-9.]/g, '')) || 0
      return val > 0
    }
    const val = parseFloat(grossAnnual.replace(/[^0-9.]/g, '')) || 0
    return val > 0 && !!STATE_TAX_RATES[selectedState] !== undefined
  }

  if (screen === 'modeSelect') {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            Help Me Set My Budget
          </h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            How would you like to calculate your recommended monthly budget?
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => handleModeSelect('direct')}
            className={cn(
              'w-full flex items-center gap-4 p-4 rounded-xl border-2 text-left',
              'bg-white dark:bg-neutral-900',
              'border-neutral-200 dark:border-neutral-700',
              'hover:border-blue-500 dark:hover:border-blue-500',
              'transition-all'
            )}
          >
            <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex-shrink-0">
              <CreditCard className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                I know my take-home pay
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                Enter what hits your bank account each paycheck
              </p>
            </div>
            <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
          </button>

          <button
            onClick={() => handleModeSelect('salary')}
            className={cn(
              'w-full flex items-center gap-4 p-4 rounded-xl border-2 text-left',
              'bg-white dark:bg-neutral-900',
              'border-neutral-200 dark:border-neutral-700',
              'hover:border-blue-500 dark:hover:border-blue-500',
              'transition-all'
            )}
          >
            <div className="p-2.5 rounded-lg bg-purple-50 dark:bg-purple-900/30 flex-shrink-0">
              <Calculator className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Calculate from salary
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                Enter your gross salary and we will estimate your take-home
              </p>
            </div>
            <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
          </button>

          <button
            onClick={onSkip}
            className={cn(
              'w-full flex items-center gap-4 p-4 rounded-xl border-2 text-left',
              'bg-white dark:bg-neutral-900',
              'border-neutral-200 dark:border-neutral-700',
              'hover:border-blue-500 dark:hover:border-blue-500',
              'transition-all'
            )}
          >
            <div className="p-2.5 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex-shrink-0">
              <PenLine className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Enter budget manually
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                Set a specific monthly amount directly
              </p>
            </div>
            <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
          </button>
        </div>

        <PrivacyNote />
      </div>
    )
  }

  if (screen === 'incomeInput') {
    if (mode === 'direct') {
      return (
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
              Your Take-Home Pay
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              What amount lands in your bank account each paycheck?
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
                Take-home amount per paycheck
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">$</span>
                <input
                  type="text"
                  inputMode="decimal"
                  value={takeHome}
                  onChange={(e) => setTakeHome(e.target.value)}
                  placeholder="2,500"
                  autoFocus
                  className={cn(
                    'w-full pl-7 pr-3 py-3 text-sm',
                    'rounded-xl border-2',
                    'bg-white dark:bg-neutral-900',
                    'border-neutral-200 dark:border-neutral-700',
                    'text-neutral-900 dark:text-neutral-100',
                    'placeholder:text-neutral-400',
                    'focus:outline-none focus:border-blue-500'
                  )}
                />
              </div>
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Not stored</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
                Pay frequency
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(FREQUENCY_LABELS) as PayFrequency[]).map((freq) => (
                  <button
                    key={freq}
                    type="button"
                    onClick={() => setFrequency(freq)}
                    className={cn(
                      'px-3 py-2.5 text-sm rounded-lg border-2 transition-all text-left',
                      frequency === freq
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500 text-blue-700 dark:text-blue-300'
                        : 'bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:border-neutral-300'
                    )}
                  >
                    {FREQUENCY_LABELS[freq]}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <PrivacyNote />

          <button
            onClick={handleIncomeNext}
            disabled={!canProceedFromIncome()}
            className={cn(
              'w-full py-3 rounded-xl text-sm font-medium transition-all',
              'bg-blue-600 text-white hover:bg-blue-700',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            Continue
          </button>
          <div className="text-center">
            <button
              onClick={() => setScreen('modeSelect')}
              className="text-sm text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
            >
              ← Back
            </button>
          </div>
        </div>
      )
    }

    // Salary mode
    return (
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            Your Salary Details
          </h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            We will estimate taxes and deductions to find your take-home
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
              Gross annual salary
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">$</span>
              <input
                type="text"
                inputMode="decimal"
                value={grossAnnual}
                onChange={(e) => setGrossAnnual(e.target.value)}
                placeholder="75,000"
                autoFocus
                className={cn(
                  'w-full pl-7 pr-3 py-3 text-sm',
                  'rounded-xl border-2',
                  'bg-white dark:bg-neutral-900',
                  'border-neutral-200 dark:border-neutral-700',
                  'text-neutral-900 dark:text-neutral-100',
                  'placeholder:text-neutral-400',
                  'focus:outline-none focus:border-blue-500'
                )}
              />
            </div>
            <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Not stored</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
              State of residence
            </label>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className={cn(
                'w-full px-3 py-3 text-sm',
                'rounded-xl border-2',
                'bg-white dark:bg-neutral-900',
                'border-neutral-200 dark:border-neutral-700',
                'text-neutral-900 dark:text-neutral-100',
                'focus:outline-none focus:border-blue-500'
              )}
            >
              {US_STATES.map((s) => (
                <option key={s.code} value={s.code}>{s.name}</option>
              ))}
            </select>
            <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Not stored</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
                401(k) contribution
              </label>
              <div className="relative">
                <input
                  type="text"
                  inputMode="decimal"
                  value={retirement401kPct}
                  onChange={(e) => setRetirement401kPct(e.target.value)}
                  placeholder="6"
                  className={cn(
                    'w-full pl-3 pr-7 py-3 text-sm',
                    'rounded-xl border-2',
                    'bg-white dark:bg-neutral-900',
                    'border-neutral-200 dark:border-neutral-700',
                    'text-neutral-900 dark:text-neutral-100',
                    'placeholder:text-neutral-400',
                    'focus:outline-none focus:border-blue-500'
                  )}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">%</span>
              </div>
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Not stored</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
                Other pre-tax deductions per month
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">$</span>
                <input
                  type="text"
                  inputMode="decimal"
                  value={monthlyHealthcare}
                  onChange={(e) => setMonthlyHealthcare(e.target.value)}
                  placeholder="0"
                  className={cn(
                    'w-full pl-7 pr-3 py-3 text-sm',
                    'rounded-xl border-2',
                    'bg-white dark:bg-neutral-900',
                    'border-neutral-200 dark:border-neutral-700',
                    'text-neutral-900 dark:text-neutral-100',
                    'placeholder:text-neutral-400',
                    'focus:outline-none focus:border-blue-500'
                  )}
                />
              </div>
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">e.g., medical, dental, parking, FSA</p>
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">Not stored</p>
            </div>
          </div>
        </div>

        <PrivacyNote />

        <button
          onClick={handleIncomeNext}
          disabled={!canProceedFromIncome()}
          className={cn(
            'w-full py-3 rounded-xl text-sm font-medium transition-all',
            'bg-blue-600 text-white hover:bg-blue-700',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          Continue
        </button>
        <div className="text-center">
          <button
            onClick={() => setScreen('modeSelect')}
            className="text-sm text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
          >
            ← Back
          </button>
        </div>
      </div>
    )
  }

  if (screen === 'savingsRate') {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            Set Your Savings Rate
          </h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            How much of your take-home do you want to set aside each month?
          </p>
        </div>

        <div className="space-y-4">
          <div className="text-center">
            <span className="text-4xl font-bold text-blue-600 dark:text-blue-400">
              {savingsRate}%
            </span>
          </div>

          <input
            type="range"
            min={5}
            max={50}
            step={1}
            value={savingsRate}
            onChange={(e) => setSavingsRate(parseInt(e.target.value))}
            className="w-full h-2 rounded-full appearance-none cursor-pointer
              bg-neutral-200 dark:bg-neutral-700
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
              [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:bg-blue-500
              [&::-webkit-slider-thumb]:cursor-pointer"
          />

          <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400">
            <span>5%</span>
            <span>50%</span>
          </div>

          <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-xs text-blue-700 dark:text-blue-300 text-center">
              The general recommendation is 20% — this gives you a comfortable spending budget while building savings.
            </p>
          </div>
        </div>

        <button
          onClick={handleSavingsNext}
          className={cn(
            'w-full py-3 rounded-xl text-sm font-medium transition-all',
            'bg-blue-600 text-white hover:bg-blue-700'
          )}
        >
          Calculate My Budget
        </button>
        <div className="text-center">
          <button
            onClick={() => setScreen('incomeInput')}
            className="text-sm text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
          >
            ← Back
          </button>
        </div>
      </div>
    )
  }

  // Result screen
  if (screen === 'result' && result) {
    const bd = result.breakdown
    return (
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            Your Recommended Budget
          </h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Based on your income and a {savingsRate}% savings rate
          </p>
        </div>

        <div className="text-center p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-1">Monthly spending budget</p>
          <p className="text-4xl font-bold text-blue-700 dark:text-blue-300">
            {formatCurrency(result.recommendedMonthlyBudget)}
          </p>
        </div>

        {bd && (
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 overflow-hidden">
            <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-900/50 border-b border-neutral-200 dark:border-neutral-800">
              <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wide">Annual breakdown</p>
            </div>
            <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {[
                { label: 'Gross income', value: bd.grossAnnual, positive: true },
                { label: '401(k) contribution', value: -bd.retirement401k },
                { label: 'Healthcare premiums', value: -bd.healthcare },
                { label: 'Federal income tax', value: -bd.federalTax },
                { label: 'State income tax', value: -bd.stateTax },
                { label: 'FICA (SS + Medicare)', value: -bd.fica },
              ].map(({ label, value, positive }) => (
                <div key={label} className="flex justify-between items-center px-4 py-2.5">
                  <span className="text-sm text-neutral-600 dark:text-neutral-400">{label}</span>
                  <span className={cn(
                    'text-sm font-medium',
                    positive
                      ? 'text-neutral-900 dark:text-neutral-100'
                      : 'text-red-600 dark:text-red-400'
                  )}>
                    {positive ? formatCurrency(value) : `(${formatCurrency(Math.abs(value))})`}
                  </span>
                </div>
              ))}
              <div className="flex justify-between items-center px-4 py-2.5 bg-neutral-50 dark:bg-neutral-900/50">
                <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Net annual</span>
                <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {formatCurrency(bd.netAnnual)}
                </span>
              </div>
              <div className="flex justify-between items-center px-4 py-2.5">
                <span className="text-sm text-neutral-600 dark:text-neutral-400">Savings ({savingsRate}%)</span>
                <span className="text-sm font-medium text-green-600 dark:text-green-400">
                  {formatCurrency(bd.savingsAmount)}
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <p className="text-xs text-amber-700 dark:text-amber-300 text-center">
            Only the final budget amount you choose to apply will be saved. Your income, deductions, and savings rate are discarded immediately.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <button
            onClick={() => onApply(Math.round(result.recommendedMonthlyBudget))}
            className={cn(
              'w-full py-3 rounded-xl text-sm font-medium transition-all',
              'bg-blue-600 text-white hover:bg-blue-700'
            )}
          >
            Use {formatCurrency(Math.round(result.recommendedMonthlyBudget))} as my budget
          </button>
          <button
            onClick={onSkip}
            className="w-full py-3 rounded-xl text-sm text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    )
  }

  return null
}
