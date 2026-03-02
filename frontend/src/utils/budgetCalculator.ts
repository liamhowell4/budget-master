const FEDERAL_BRACKETS = [
  { rate: 0.10, min: 0, max: 11925 },
  { rate: 0.12, min: 11925, max: 48475 },
  { rate: 0.22, min: 48475, max: 103350 },
  { rate: 0.24, min: 103350, max: 197300 },
  { rate: 0.32, min: 197300, max: 250525 },
  { rate: 0.35, min: 250525, max: 626350 },
  { rate: 0.37, min: 626350, max: Infinity },
]

const STANDARD_DEDUCTION = 14600
const SS_WAGE_BASE = 176100
const SS_RATE = 0.062
const MEDICARE_RATE = 0.0145

export const STATE_TAX_RATES: Record<string, number> = {
  AL: 0.05, AK: 0, AZ: 0.025, AR: 0.044, CA: 0.093,
  CO: 0.044, CT: 0.065, DE: 0.066, FL: 0, GA: 0.055,
  HI: 0.079, ID: 0.058, IL: 0.0495, IN: 0.03, IA: 0.06,
  KS: 0.057, KY: 0.04, LA: 0.042, ME: 0.075, MD: 0.0575,
  MA: 0.05, MI: 0.0425, MN: 0.0785, MS: 0.047, MO: 0.054,
  MT: 0.059, NE: 0.0664, NV: 0, NH: 0, NJ: 0.0637,
  NM: 0.059, NY: 0.0685, NC: 0.0475, ND: 0.029, OH: 0.04,
  OK: 0.0475, OR: 0.099, PA: 0.0307, RI: 0.0599, SC: 0.064,
  SD: 0, TN: 0, TX: 0, UT: 0.0465, VT: 0.0666,
  VA: 0.0575, WA: 0, WV: 0.065, WI: 0.0765, WY: 0, DC: 0.085,
}

export const US_STATES = [
  { code: 'AL', name: 'Alabama' }, { code: 'AK', name: 'Alaska' },
  { code: 'AZ', name: 'Arizona' }, { code: 'AR', name: 'Arkansas' },
  { code: 'CA', name: 'California' }, { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' }, { code: 'DE', name: 'Delaware' },
  { code: 'FL', name: 'Florida' }, { code: 'GA', name: 'Georgia' },
  { code: 'HI', name: 'Hawaii' }, { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' }, { code: 'IN', name: 'Indiana' },
  { code: 'IA', name: 'Iowa' }, { code: 'KS', name: 'Kansas' },
  { code: 'KY', name: 'Kentucky' }, { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' }, { code: 'MD', name: 'Maryland' },
  { code: 'MA', name: 'Massachusetts' }, { code: 'MI', name: 'Michigan' },
  { code: 'MN', name: 'Minnesota' }, { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' }, { code: 'MT', name: 'Montana' },
  { code: 'NE', name: 'Nebraska' }, { code: 'NV', name: 'Nevada' },
  { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' }, { code: 'NY', name: 'New York' },
  { code: 'NC', name: 'North Carolina' }, { code: 'ND', name: 'North Dakota' },
  { code: 'OH', name: 'Ohio' }, { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' }, { code: 'PA', name: 'Pennsylvania' },
  { code: 'RI', name: 'Rhode Island' }, { code: 'SC', name: 'South Carolina' },
  { code: 'SD', name: 'South Dakota' }, { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' }, { code: 'UT', name: 'Utah' },
  { code: 'VT', name: 'Vermont' }, { code: 'VA', name: 'Virginia' },
  { code: 'WA', name: 'Washington' }, { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' }, { code: 'WY', name: 'Wyoming' },
  { code: 'DC', name: 'Washington, D.C.' },
]

function calcFederalTax(taxableIncome: number): number {
  if (taxableIncome <= 0) return 0
  let tax = 0
  for (const bracket of FEDERAL_BRACKETS) {
    if (taxableIncome <= bracket.min) break
    const taxableInBracket = Math.min(taxableIncome, bracket.max) - bracket.min
    tax += taxableInBracket * bracket.rate
  }
  return tax
}

export type PayFrequency = 'weekly' | 'biweekly' | 'semimonthly' | 'monthly'

export interface DirectDepositInput {
  mode: 'direct'
  takeHome: number
  frequency: PayFrequency
  savingsRate: number
}

export interface SalaryInput {
  mode: 'salary'
  grossAnnual: number
  state: string
  retirement401kPct: number
  monthlyHealthcare: number
  savingsRate: number
}

export interface BudgetCalculationResult {
  recommendedMonthlyBudget: number
  breakdown?: {
    grossAnnual: number
    retirement401k: number
    healthcare: number
    federalTax: number
    stateTax: number
    fica: number
    netAnnual: number
    savingsAmount: number
  }
}

const FREQUENCY_MULTIPLIERS: Record<PayFrequency, number> = {
  weekly: 52,
  biweekly: 26,
  semimonthly: 24,
  monthly: 12,
}

export function calculateBudget(input: DirectDepositInput | SalaryInput): BudgetCalculationResult {
  if (input.mode === 'direct') {
    const annualTakeHome = input.takeHome * FREQUENCY_MULTIPLIERS[input.frequency]
    const monthlyTakeHome = annualTakeHome / 12
    const recommendedMonthlyBudget = monthlyTakeHome * (1 - input.savingsRate / 100)
    return { recommendedMonthlyBudget }
  }

  const { grossAnnual, state, retirement401kPct, monthlyHealthcare, savingsRate } = input

  const retirement401k = grossAnnual * (retirement401kPct / 100)
  const annualHealthcare = monthlyHealthcare * 12

  // FICA on gross (SS capped at wage base, Medicare uncapped)
  const ssWages = Math.min(grossAnnual, SS_WAGE_BASE)
  const ssTax = ssWages * SS_RATE
  const medicareTax = grossAnnual * MEDICARE_RATE
  const fica = ssTax + medicareTax

  // Federal taxable income: gross - 401k - standard deduction
  const federalTaxable = Math.max(0, grossAnnual - retirement401k - STANDARD_DEDUCTION)
  const federalTax = calcFederalTax(federalTaxable)

  // State tax on gross (approximate — most states don't allow 401k deduction in same way)
  const stateRate = STATE_TAX_RATES[state] ?? 0
  const stateTax = grossAnnual * stateRate

  const netAnnual = grossAnnual - retirement401k - annualHealthcare - federalTax - stateTax - fica
  const monthlyNet = netAnnual / 12
  const savingsAmount = monthlyNet * (savingsRate / 100)
  const recommendedMonthlyBudget = monthlyNet * (1 - savingsRate / 100)

  return {
    recommendedMonthlyBudget: Math.max(0, recommendedMonthlyBudget),
    breakdown: {
      grossAnnual,
      retirement401k,
      healthcare: annualHealthcare,
      federalTax,
      stateTax,
      fica,
      netAnnual: Math.max(0, netAnnual),
      savingsAmount: Math.max(0, savingsAmount),
    },
  }
}
