import { Wrench } from 'lucide-react'
import type { ToolCall } from '@/types/chat'
import { ExpenseCard } from './ExpenseCard'

interface ToolCallDisplayProps {
  toolCall: ToolCall
  budgetWarning?: string
  onExpenseDelete?: (expenseId: string) => void
  onExpenseEdit?: (expenseId: string, updates: { name?: string; amount?: number }) => void
}

interface SaveExpenseResult {
  success: boolean
  expense_id: string
  expense_name: string
  amount: number
  category: string
  date?: { day: number; month: number; year: number }
}

function isSaveExpenseResult(result: unknown): result is SaveExpenseResult {
  return (
    typeof result === 'object' &&
    result !== null &&
    'success' in result &&
    'expense_id' in result &&
    'expense_name' in result &&
    'amount' in result &&
    'category' in result
  )
}

export function ToolCallDisplay({ toolCall, budgetWarning, onExpenseDelete, onExpenseEdit }: ToolCallDisplayProps) {
  // Render ExpenseCard for successful save_expense calls
  if (toolCall.name === 'save_expense' && isSaveExpenseResult(toolCall.result)) {
    // Include date from tool args if not in result
    const result = toolCall.result
    if (!result.date && toolCall.args?.date) {
      result.date = toolCall.args.date as { day: number; month: number; year: number }
    }
    return (
      <ExpenseCard
        result={result}
        budgetWarning={budgetWarning}
        onDelete={onExpenseDelete}
        onEdit={onExpenseEdit}
      />
    )
  }

  // Default: show wrench icon + tool name for other tools
  return (
    <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
      <Wrench className="h-3.5 w-3.5" />
      <span className="font-mono text-xs">{toolCall.name}</span>
    </div>
  )
}
