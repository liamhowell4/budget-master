import type { ExpenseDate } from '@/types/expense'

/**
 * Format a number as currency (USD)
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

/**
 * Format an ExpenseDate object to a readable string
 */
export function formatExpenseDate(date: ExpenseDate): string {
  const d = new Date(date.year, date.month - 1, date.day)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Format a Date object to a readable string
 */
export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Get month name from month number (1-12)
 */
export function getMonthName(month: number): string {
  const date = new Date(2024, month - 1, 1)
  return date.toLocaleDateString('en-US', { month: 'long' })
}

/**
 * Format a timestamp string to a time like "2:30 PM"
 */
export function formatExpenseTime(timestamp: string): string {
  const d = new Date(timestamp)
  return d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

/**
 * Format an ExpenseDate + optional timestamp to "Jan 15, 2026 at 2:30 PM"
 */
export function formatExpenseDateTime(date: ExpenseDate, timestamp?: string): string {
  const dateStr = formatExpenseDate(date)
  if (timestamp) {
    const timeStr = formatExpenseTime(timestamp)
    return `${dateStr} at ${timeStr}`
  }
  return dateStr
}

/**
 * Format percentage with specified decimal places
 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`
}
