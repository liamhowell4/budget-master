import { ExpenseType } from '@/types/expense'

// Icon names from Lucide React - use with <Icon name={CATEGORY_ICONS[category]} />
export const CATEGORY_ICONS: Record<ExpenseType, string> = {
  FOOD_OUT: 'utensils',
  COFFEE: 'coffee',
  GROCERIES: 'shopping-cart',
  RENT: 'home',
  UTILITIES: 'lightbulb',
  MEDICAL: 'heart-pulse',
  GAS: 'fuel',
  RIDE_SHARE: 'car',
  HOTEL: 'bed',
  TECH: 'laptop',
  TRAVEL: 'plane',
  OTHER: 'package',
}

export const CATEGORY_LABELS: Record<ExpenseType, string> = {
  FOOD_OUT: 'Dining Out',
  COFFEE: 'Coffee',
  GROCERIES: 'Groceries',
  RENT: 'Rent',
  UTILITIES: 'Utilities',
  MEDICAL: 'Medical',
  GAS: 'Gas',
  RIDE_SHARE: 'Ride Share',
  HOTEL: 'Hotel',
  TECH: 'Tech',
  TRAVEL: 'Travel',
  OTHER: 'Other',
}

export const BUDGET_THRESHOLDS = {
  INFO: 50,
  WARNING: 90,
  DANGER: 95,
  OVER: 100,
} as const

// Pastel background colors for expense cards
// bg: combined light + dark background classes, accent: text color classes
export const CATEGORY_COLORS: Record<ExpenseType, { bg: string; accent: string }> = {
  FOOD_OUT: { bg: 'bg-emerald-50 dark:bg-emerald-950/40', accent: 'text-emerald-600 dark:text-emerald-400' },
  COFFEE: { bg: 'bg-amber-50 dark:bg-amber-950/40', accent: 'text-amber-600 dark:text-amber-400' },
  GROCERIES: { bg: 'bg-teal-50 dark:bg-teal-950/40', accent: 'text-teal-600 dark:text-teal-400' },
  RENT: { bg: 'bg-slate-100 dark:bg-slate-900/60', accent: 'text-slate-600 dark:text-slate-400' },
  UTILITIES: { bg: 'bg-sky-50 dark:bg-sky-950/40', accent: 'text-sky-600 dark:text-sky-400' },
  MEDICAL: { bg: 'bg-rose-50 dark:bg-rose-950/40', accent: 'text-rose-600 dark:text-rose-400' },
  GAS: { bg: 'bg-orange-50 dark:bg-orange-950/40', accent: 'text-orange-600 dark:text-orange-400' },
  RIDE_SHARE: { bg: 'bg-violet-50 dark:bg-violet-950/40', accent: 'text-violet-600 dark:text-violet-400' },
  HOTEL: { bg: 'bg-indigo-50 dark:bg-indigo-950/40', accent: 'text-indigo-600 dark:text-indigo-400' },
  TECH: { bg: 'bg-cyan-50 dark:bg-cyan-950/40', accent: 'text-cyan-600 dark:text-cyan-400' },
  TRAVEL: { bg: 'bg-blue-50 dark:bg-blue-950/40', accent: 'text-blue-600 dark:text-blue-400' },
  OTHER: { bg: 'bg-neutral-100 dark:bg-neutral-800/60', accent: 'text-neutral-600 dark:text-neutral-400' },
}

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
