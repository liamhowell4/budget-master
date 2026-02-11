/**
 * Shared date type for tool results
 */
export interface ToolDate {
  day: number
  month: number
  year: number
}

/**
 * Format a tool result date as "Today" / "Yesterday" / "Jan 5"
 */
export function formatToolDate(date: ToolDate): string {
  const d = new Date(date.year, date.month - 1, date.day)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/**
 * Format a date range as "Jan 1 - Jan 31, 2026"
 */
export function formatDateRange(start: ToolDate, end: ToolDate): string {
  const s = new Date(start.year, start.month - 1, start.day)
  const e = new Date(end.year, end.month - 1, end.day)

  const sMonth = s.toLocaleDateString('en-US', { month: 'short' })
  const eMonth = e.toLocaleDateString('en-US', { month: 'short' })

  if (start.year === end.year) {
    if (start.month === end.month) {
      return `${sMonth} ${start.day} - ${end.day}, ${start.year}`
    }
    return `${sMonth} ${start.day} - ${eMonth} ${end.day}, ${start.year}`
  }
  return `${sMonth} ${start.day}, ${start.year} - ${eMonth} ${end.day}, ${end.year}`
}
