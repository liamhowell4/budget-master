import { Wrench } from 'lucide-react'
import type { ToolCall } from '@/types/chat'
import { ExpenseCard } from './ExpenseCard'
import { SpendingSummaryCard, isSpendingSummaryResult } from './SpendingSummaryCard'
import { BudgetRemainingCard, isBudgetRemainingResult } from './BudgetRemainingCard'
import { PeriodComparisonCard, isComparePeriodsResult } from './PeriodComparisonCard'
import { TopExpensesCard, isLargestExpensesResult } from './TopExpensesCard'
import { ExpenseListCard, isExpenseListResult } from './ExpenseListCard'
import { SpendingByCategoryCard, isSpendingByCategoryResult } from './SpendingByCategoryCard'
import {
  RecurringExpenseCard,
  isCreateRecurringResult,
  isListRecurringResult,
} from './RecurringExpenseCard'

interface ToolCallDisplayProps {
  toolCall: ToolCall
  budgetWarning?: string
  deletedExpenseIds?: Set<string>
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

export function ToolCallDisplay({ toolCall, budgetWarning, deletedExpenseIds, onExpenseDelete, onExpenseEdit }: ToolCallDisplayProps) {
  // Render ExpenseCard for successful save_expense calls
  if (toolCall.name === 'save_expense' && isSaveExpenseResult(toolCall.result)) {
    // Include date from tool args if not in result
    const result = toolCall.result
    if (!result.date && toolCall.args?.date) {
      result.date = toolCall.args.date as { day: number; month: number; year: number }
    }
    const isDeleted = deletedExpenseIds?.has(result.expense_id) ?? false
    return (
      <ExpenseCard
        result={result}
        budgetWarning={budgetWarning}
        initialDeleted={isDeleted}
        onDelete={onExpenseDelete}
        onEdit={onExpenseEdit}
      />
    )
  }

  // Spending summary
  if (toolCall.name === 'get_spending_summary' && isSpendingSummaryResult(toolCall.result)) {
    return <SpendingSummaryCard result={toolCall.result} />
  }

  // Budget remaining
  if (toolCall.name === 'get_budget_remaining' && isBudgetRemainingResult(toolCall.result)) {
    return <BudgetRemainingCard result={toolCall.result} />
  }

  // Period comparison
  if (toolCall.name === 'compare_periods' && isComparePeriodsResult(toolCall.result)) {
    return <PeriodComparisonCard result={toolCall.result} />
  }

  // Largest expenses
  if (toolCall.name === 'get_largest_expenses' && isLargestExpensesResult(toolCall.result)) {
    return <TopExpensesCard result={toolCall.result} />
  }

  // Expense lists (recent, search, query)
  if (
    (toolCall.name === 'get_recent_expenses' ||
      toolCall.name === 'search_expenses' ||
      toolCall.name === 'query_expenses') &&
    isExpenseListResult(toolCall.result)
  ) {
    return <ExpenseListCard result={toolCall.result} toolName={toolCall.name} />
  }

  // Spending by category
  if (toolCall.name === 'get_spending_by_category' && isSpendingByCategoryResult(toolCall.result)) {
    return <SpendingByCategoryCard result={toolCall.result} />
  }

  // Create recurring expense
  if (toolCall.name === 'create_recurring_expense' && isCreateRecurringResult(toolCall.result)) {
    return <RecurringExpenseCard mode="create" createResult={toolCall.result} />
  }

  // List recurring expenses
  if (toolCall.name === 'list_recurring_expenses' && isListRecurringResult(toolCall.result)) {
    return <RecurringExpenseCard mode="list" listResult={toolCall.result} />
  }

  // Default: show wrench icon + tool name for other tools
  return (
    <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
      <Wrench className="h-3.5 w-3.5" />
      <span className="font-mono text-xs">{toolCall.name}</span>
    </div>
  )
}
