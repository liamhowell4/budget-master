import { cn } from '@/utils/cn'
import type { ChatMessage as ChatMessageType, ToolCall } from '@/types/chat'
import { ToolCallDisplay } from './ToolCallDisplay'

interface ChatMessageProps {
  message: ChatMessageType
  deletedExpenseIds?: Set<string>
  onExpenseDelete?: (expenseId: string) => void
  onExpenseEdit?: (expenseId: string, updates: { name?: string; amount?: number }) => void
}

// Extract budget warning from get_budget_status tool result
function extractBudgetWarning(toolCalls: ToolCall[]): string | undefined {
  const budgetTool = toolCalls.find((tc) => tc.name === 'get_budget_status')
  if (!budgetTool?.result) return undefined

  // Result can be an object with budget_warning or a string
  if (typeof budgetTool.result === 'object' && 'budget_warning' in budgetTool.result) {
    return budgetTool.result.budget_warning as string
  }
  return undefined
}

// Check if we have the save_expense + get_budget_status pattern
function hasSaveExpenseWithBudget(toolCalls: ToolCall[]): boolean {
  const hasSaveExpense = toolCalls.some((tc) => tc.name === 'save_expense')
  const hasBudgetStatus = toolCalls.some((tc) => tc.name === 'get_budget_status')
  return hasSaveExpense && hasBudgetStatus
}

export function ChatMessage({ message, deletedExpenseIds, onExpenseDelete, onExpenseEdit }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const hasToolCalls = !isUser && message.toolCalls && message.toolCalls.length > 0
  const hasContent = message.content.trim().length > 0

  // Check if this is a save_expense + get_budget_status pattern
  const isExpenseWithBudgetPattern = hasToolCalls && hasSaveExpenseWithBudget(message.toolCalls!)
  const budgetWarning = hasToolCalls ? extractBudgetWarning(message.toolCalls!) : undefined

  // Filter out get_budget_status tool if we're showing expense card with budget info
  const toolCallsToRender = hasToolCalls
    ? isExpenseWithBudgetPattern
      ? message.toolCalls!.filter((tc) => tc.name !== 'get_budget_status')
      : message.toolCalls!
    : []

  // Hide text content when we have expense card with budget info
  const shouldShowContent = hasContent && !isExpenseWithBudgetPattern

  return (
    <div className="space-y-2">
      {/* Tool calls - flush with background, no bubble */}
      {toolCallsToRender.length > 0 && (
        <div className="space-y-1.5">
          {toolCallsToRender.map((toolCall) => (
            <ToolCallDisplay
              key={toolCall.id}
              toolCall={toolCall}
              budgetWarning={toolCall.name === 'save_expense' ? budgetWarning : undefined}
              deletedExpenseIds={deletedExpenseIds}
              onExpenseDelete={onExpenseDelete}
              onExpenseEdit={onExpenseEdit}
            />
          ))}
        </div>
      )}

      {/* Message content */}
      {shouldShowContent && (
        <div
          className={cn(
            'flex w-full',
            isUser ? 'justify-end' : 'justify-start'
          )}
        >
          <div
            className={cn(
              'max-w-[85%] rounded-lg px-3.5 py-2.5',
              isUser
                ? 'bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 border border-neutral-200 dark:border-neutral-700'
            )}
          >
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
          </div>
        </div>
      )}
    </div>
  )
}
