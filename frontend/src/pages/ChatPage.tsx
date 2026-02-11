import { useEffect, useRef, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatInput, ChatMessage } from '@/components/chat'
import { useChat } from '@/hooks/useChat'
import { useBudget, invalidateBudgetCache } from '@/hooks/useBudget'
import { useExpenses, invalidateExpensesCache } from '@/hooks/useExpenses'
import { useCategories } from '@/hooks/useCategories'
import { deleteExpense, updateExpense } from '@/services/expenseService'
import { formatConversationTitle, markExpenseDeleted } from '@/services/conversationService'
import { useAuth } from '@/contexts/AuthContext'
import { useServer } from '@/contexts/ServerContext'
import { Card, ProgressBar, Spinner, CategoryIcon, ExpenseEditModal, Modal } from '@/components/ui'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import {
  PanelRightClose,
  PanelRight,
  PanelLeftClose,
  PanelLeft,
  RefreshCw,
  ArrowUpDown,
  Plus,
  MessageSquare,
  Trash2,
} from 'lucide-react'
import type { Expense } from '@/types/expense'
import type { BudgetCategory } from '@/types/budget'

const CATEGORY_LABELS: Record<string, string> = {
  FOOD_OUT: 'Dining',
  COFFEE: 'Coffee',
  GROCERIES: 'Groceries',
  RENT: 'Rent',
  UTILITIES: 'Utilities',
  MEDICAL: 'Medical',
  GAS: 'Gas',
  RIDE_SHARE: 'Rides',
  HOTEL: 'Hotel',
  TECH: 'Tech',
  TRAVEL: 'Travel',
  OTHER: 'Other',
}

type SortOption = 'date-desc' | 'date-asc' | 'amount-desc' | 'amount-asc'

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'date-desc', label: 'Newest first' },
  { value: 'date-asc', label: 'Oldest first' },
  { value: 'amount-desc', label: 'Highest amount' },
  { value: 'amount-asc', label: 'Lowest amount' },
]

function sortExpenses(expenses: Expense[], sortBy: SortOption): Expense[] {
  return [...expenses].sort((a, b) => {
    switch (sortBy) {
      case 'date-desc':
        return (
          new Date(b.date.year, b.date.month - 1, b.date.day).getTime() -
          new Date(a.date.year, a.date.month - 1, a.date.day).getTime()
        )
      case 'date-asc':
        return (
          new Date(a.date.year, a.date.month - 1, a.date.day).getTime() -
          new Date(b.date.year, b.date.month - 1, b.date.day).getTime()
        )
      case 'amount-desc':
        return b.amount - a.amount
      case 'amount-asc':
        return a.amount - b.amount
      default:
        return 0
    }
  })
}

function CategoryExpensesModal({
  category,
  isOpen,
  onClose,
}: {
  category: BudgetCategory | null
  isOpen: boolean
  onClose: () => void
}) {
  const [sortBy, setSortBy] = useState<SortOption>('date-desc')
  const now = new Date()
  const { expenses, loading } = useExpenses(
    now.getFullYear(),
    now.getMonth() + 1,
    category?.category
  )

  const sortedExpenses = useMemo(() => sortExpenses(expenses, sortBy), [expenses, sortBy])

  const stats = useMemo(() => {
    if (expenses.length === 0) return null
    const total = expenses.reduce((sum, e) => sum + e.amount, 0)
    return {
      total,
      count: expenses.length,
      average: total / expenses.length,
    }
  }, [expenses])

  if (!category) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${CATEGORY_LABELS[category.category] || category.category} Expenses`}
      className="max-w-lg"
    >
      <div className="space-y-4">
        {/* Stats summary */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 rounded-lg bg-[var(--surface-secondary)]">
            <p className="text-xs text-[var(--text-muted)]">Spent</p>
            <p className="text-lg font-semibold text-[var(--text-primary)]">
              {formatCurrency(category.spending)}
            </p>
          </div>
          <div className="text-center p-3 rounded-lg bg-[var(--surface-secondary)]">
            <p className="text-xs text-[var(--text-muted)]">Budget</p>
            <p className="text-lg font-semibold text-[var(--text-primary)]">
              {formatCurrency(category.cap)}
            </p>
          </div>
          <div className="text-center p-3 rounded-lg bg-[var(--surface-secondary)]">
            <p className="text-xs text-[var(--text-muted)]">Remaining</p>
            <p
              className={cn(
                'text-lg font-semibold',
                category.remaining >= 0
                  ? 'text-[var(--success)]'
                  : 'text-[var(--error)]'
              )}
            >
              {formatCurrency(category.remaining)}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <ProgressBar percentage={category.percentage} />

        {/* Sort dropdown */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-[var(--text-muted)]">
            {stats ? `${stats.count} expense${stats.count !== 1 ? 's' : ''}` : 'No expenses'}
          </p>
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className={cn(
                'appearance-none pl-8 pr-3 py-1.5 rounded-md text-xs',
                'bg-[var(--surface-secondary)]',
                'border border-[var(--border-primary)]',
                'text-[var(--text-secondary)]',
                'focus:outline-none focus:border-[var(--border-focus)]',
                'cursor-pointer'
              )}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--text-muted)] pointer-events-none" />
          </div>
        </div>

        {/* Expense list */}
        {loading ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : sortedExpenses.length === 0 ? (
          <div className="text-center py-8 text-sm text-[var(--text-muted)]">
            No expenses in this category
          </div>
        ) : (
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {sortedExpenses.map((expense) => (
              <div
                key={expense.id}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg',
                  'bg-[var(--surface-secondary)]'
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                    {expense.expense_name}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {formatExpenseDate(expense.date)}
                  </p>
                </div>
                <p className="text-sm font-medium text-[var(--text-primary)] ml-3">
                  {formatCurrency(expense.amount)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Average spending */}
        {stats && stats.count > 1 && (
          <div className="pt-3 border-t border-[var(--border-primary)]">
            <p className="text-xs text-[var(--text-muted)] text-center">
              Average: {formatCurrency(stats.average)} per expense
            </p>
          </div>
        )}
      </div>
    </Modal>
  )
}

export function ChatPage() {
  const navigate = useNavigate()
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    sendAudio,
    conversations,
    currentConversationId,
    conversationsLoading,
    loadConversations,
    loadConversation,
    startNewConversation,
    removeConversation,
    deletedExpenseIds,
    addDeletedExpenseId,
  } = useChat()
  const { getToken } = useAuth()
  const { budget } = useBudget()
  const { expenses } = useExpenses()
  const { categories } = useCategories()
  const { isConnected, isConnecting, error: serverError, reconnect } = useServer()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  // Default sidebars open on desktop (lg+), closed on mobile
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(() =>
    typeof window !== 'undefined' && window.innerWidth >= 1024
  )
  const [rightSidebarOpen, setRightSidebarOpen] = useState(() =>
    typeof window !== 'undefined' && window.innerWidth >= 1024
  )
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<BudgetCategory | null>(null)

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handlers for expense card actions - call API directly
  const handleExpenseDelete = async (expenseId: string) => {
    try {
      await deleteExpense(expenseId)
      // Track locally for immediate UI feedback
      addDeletedExpenseId(expenseId)
      // Persist to conversation so reload shows deleted state
      if (currentConversationId) {
        const token = await getToken()
        if (token) {
          markExpenseDeleted(token, currentConversationId, expenseId).catch((err) =>
            console.error('Failed to persist deleted expense to conversation:', err)
          )
        }
      }
      // Invalidate caches so sidebar and other views update
      invalidateExpensesCache()
      invalidateBudgetCache()
    } catch (err) {
      console.error('Failed to delete expense:', err)
    }
  }

  const handleExpenseEdit = async (expenseId: string, updates: { name?: string; amount?: number; category?: string }) => {
    try {
      await updateExpense(expenseId, {
        expense_name: updates.name,
        amount: updates.amount,
        category: updates.category,
      })
      // Invalidate caches so sidebar and other views update
      invalidateExpensesCache()
      invalidateBudgetCache()
    } catch (err) {
      console.error('Failed to update expense:', err)
    }
  }

  const handleSidebarExpenseSave = async (expenseId: string, updates: { expense_name?: string; amount?: number; category?: string }) => {
    await updateExpense(expenseId, updates)
    invalidateExpensesCache()
    invalidateBudgetCache()
  }

  const handleSidebarExpenseDelete = async (expenseId: string) => {
    await deleteExpense(expenseId)
    invalidateExpensesCache()
    invalidateBudgetCache()
  }

  const activeCategories = budget?.categories
    .filter((cat) => cat.cap > 0)
    .sort((a, b) => {
      const aOrder = categories.find((c) => c.category_id === a.category)?.sort_order ?? 999
      const bOrder = categories.find((c) => c.category_id === b.category)?.sort_order ?? 999
      return aOrder - bOrder
    })
    .slice(0, 4) || []

  return (
    <div className="flex h-[calc(100dvh-56px)]">
        {/* Left sidebar - Conversation History */}
        <aside
          className={cn(
            'w-64 border-r border-[var(--border-primary)]',
            'bg-[var(--bg-secondary)] overflow-y-auto',
            'transition-transform duration-200 ease-out',
            // Mobile/tablet: fixed overlay
            'fixed inset-y-0 left-0 z-20 top-14',
            leftSidebarOpen ? 'translate-x-0' : '-translate-x-full',
            // Large screens: inline, part of flex layout
            'lg:relative lg:top-0 lg:z-0 lg:flex-shrink-0 lg:translate-x-0'
          )}
        >
          <div className="p-3 space-y-2">
            {/* New Chat Button */}
            <button
              onClick={startNewConversation}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2.5 rounded-lg',
                'bg-[var(--surface-primary)]',
                'border border-[var(--border-primary)]',
                'text-[var(--text-secondary)]',
                'hover:bg-[var(--surface-hover)]',
                'transition-colors text-sm font-medium'
              )}
            >
              <Plus className="h-4 w-4" />
              New Chat
            </button>

            {/* Conversation List */}
            <div className="pt-2">
              <h3 className="px-2 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-2">
                Recent
              </h3>
              {conversationsLoading ? (
                <div className="flex justify-center py-4">
                  <Spinner size="sm" />
                </div>
              ) : conversations.length === 0 ? (
                <p className="px-2 text-xs text-[var(--text-muted)]">
                  No conversations yet
                </p>
              ) : (
                <div className="space-y-1">
                  {conversations.map((conv) => (
                    <div
                      key={conv.conversation_id}
                      className={cn(
                        'group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer',
                        'hover:bg-[var(--surface-primary)]',
                        'transition-colors',
                        currentConversationId === conv.conversation_id &&
                          'bg-[var(--surface-primary)] border border-[var(--border-primary)]'
                      )}
                      onClick={() => loadConversation(conv.conversation_id)}
                    >
                      <MessageSquare className="h-4 w-4 text-[var(--text-muted)] flex-shrink-0" />
                      <span className="flex-1 text-sm text-[var(--text-secondary)] truncate">
                        {formatConversationTitle(conv)}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          removeConversation(conv.conversation_id)
                        }}
                        className={cn(
                          'opacity-0 group-hover:opacity-100',
                          'p-1 rounded hover:bg-[var(--surface-hover)]',
                          'text-[var(--text-muted)] hover:text-[var(--error)]',
                          'transition-all'
                        )}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </aside>

        {/* Left sidebar backdrop - only on smaller screens */}
        {leftSidebarOpen && (
          <div
            className="fixed inset-0 bg-black/20 z-10 lg:hidden"
            onClick={() => setLeftSidebarOpen(false)}
          />
        )}

        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
              {messages.length === 0 ? (
                <div className="flex h-full min-h-[50vh] items-center justify-center">
                  <div className="text-center">
                    <h2 className="text-lg font-medium text-[var(--text-primary)] mb-1">
                      Track your expenses
                    </h2>
                    <p className="text-sm text-[var(--text-muted)] mb-4">
                      Start a conversation to log and manage your spending
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {['Coffee $5', 'Lunch $15', 'Groceries $80'].map((example) => (
                        <button
                          key={example}
                          onClick={() => sendMessage(example)}
                          className={cn(
                            'px-3 py-1.5 rounded-md text-sm',
                            'bg-[var(--surface-secondary)]',
                            'border border-[var(--border-primary)]',
                            'text-[var(--text-secondary)]',
                            'hover:bg-[var(--surface-hover)]',
                            'transition-colors'
                          )}
                        >
                          {example}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                      deletedExpenseIds={deletedExpenseIds}
                      onExpenseDelete={handleExpenseDelete}
                      onExpenseEdit={handleExpenseEdit}
                    />
                  ))}

                  {isLoading && messages[messages.length - 1]?.content === '' && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                        <Spinner size="sm" />
                        <span>Thinking...</span>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>

          {/* Connection status / Error display */}
          {(isConnecting || serverError || error) && (
            <div className="px-4 pb-2 max-w-2xl mx-auto w-full">
              {isConnecting && (
                <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                  <Spinner size="sm" />
                  <span>Connecting to server...</span>
                </div>
              )}
              {serverError && !isConnecting && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-[var(--warning)]">{serverError}</p>
                  <button
                    onClick={reconnect}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm',
                      'bg-[var(--surface-secondary)]',
                      'text-[var(--text-secondary)]',
                      'hover:bg-[var(--surface-hover)]',
                      'transition-colors'
                    )}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry
                  </button>
                </div>
              )}
              {error && !serverError && (
                <p className="text-sm text-[var(--error)]">{error}</p>
              )}
            </div>
          )}

          {/* Chat input */}
          <div className="border-t border-[var(--border-primary)] bg-[var(--bg-primary)]">
            <div className="max-w-2xl mx-auto px-4 py-4">
              <ChatInput
                onSendMessage={sendMessage}
                onSendAudio={sendAudio}
                disabled={isLoading || !isConnected}
              />
            </div>
          </div>
        </div>

        {/* Sidebar toggle buttons - only visible on smaller screens */}
        <button
          onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
          className={cn(
            'fixed bottom-24 left-4 z-30 lg:hidden',
            'p-3 rounded-full shadow-lg',
            'bg-[var(--surface-primary)]',
            'border border-[var(--border-primary)]',
            'text-[var(--text-secondary)]',
            'hover:bg-[var(--surface-hover)]',
            'transition-colors'
          )}
          aria-label={leftSidebarOpen ? 'Close history' : 'Open history'}
        >
          {leftSidebarOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeft className="h-5 w-5" />}
        </button>
        <button
          onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
          className={cn(
            'fixed bottom-24 right-4 z-30 lg:hidden',
            'p-3 rounded-full shadow-lg',
            'bg-[var(--surface-primary)]',
            'border border-[var(--border-primary)]',
            'text-[var(--text-secondary)]',
            'hover:bg-[var(--surface-hover)]',
            'transition-colors'
          )}
          aria-label={rightSidebarOpen ? 'Close budget' : 'Open budget'}
        >
          {rightSidebarOpen ? <PanelRightClose className="h-5 w-5" /> : <PanelRight className="h-5 w-5" />}
        </button>

        {/* Right sidebar */}
        <aside
          className={cn(
            'w-80 border-l border-[var(--border-primary)]',
            'bg-[var(--bg-primary)] overflow-y-auto',
            'transition-transform duration-200 ease-out',
            // Mobile/tablet: fixed overlay
            'fixed inset-y-0 right-0 z-20 top-14',
            rightSidebarOpen ? 'translate-x-0' : 'translate-x-full',
            // Large screens: inline, part of flex layout, always visible
            'lg:relative lg:top-0 lg:z-0 lg:flex-shrink-0 lg:translate-x-0'
          )}
        >
          <div className="p-4 space-y-6">
            {/* Monthly Summary */}
            {budget && (
              <div>
                <h3 className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-3">
                  {budget.month_name}
                </h3>
                <button
                  onClick={() => navigate('/dashboard')}
                  className="w-full text-left"
                >
                  <Card padding="sm" hover>
                    <div className="space-y-3">
                      <div className="flex items-baseline justify-between">
                        <span className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">
                          {formatCurrency(budget.total_remaining)}
                        </span>
                        <span className="text-xs text-[var(--text-muted)]">
                          remaining
                        </span>
                      </div>
                      <ProgressBar percentage={budget.total_percentage} />
                      <div className="flex justify-between text-xs text-[var(--text-muted)]">
                        <span>{formatCurrency(budget.total_spending)} spent</span>
                        <span>{formatCurrency(budget.total_cap)} budget</span>
                      </div>
                    </div>
                  </Card>
                </button>
              </div>
            )}

            {/* Category Breakdown */}
            {activeCategories.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-3">
                  Top Categories
                </h3>
                <div className="space-y-2">
                  {activeCategories.map((cat) => (
                    <button
                      key={cat.category}
                      onClick={() => setSelectedCategory(cat)}
                      className="w-full text-left"
                    >
                      <Card padding="sm" hover>
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--surface-secondary)]">
                            <CategoryIcon
                              category={cat.category}
                              className="h-4 w-4 text-[var(--text-muted)]"
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-[var(--text-primary)]">
                                {CATEGORY_LABELS[cat.category] || cat.category}
                              </span>
                              <span className="text-xs text-[var(--text-muted)]">
                                {cat.percentage.toFixed(0)}% | {formatCurrency(cat.remaining)} left
                              </span>
                            </div>
                            <ProgressBar percentage={cat.percentage} size="sm" />
                          </div>
                        </div>
                      </Card>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Expenses */}
            {expenses && expenses.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-3">
                  Recent
                </h3>
                <div className="space-y-1">
                  {expenses.slice(0, 5).map((expense) => (
                    <button
                      key={expense.id}
                      onClick={() => setSelectedExpense(expense)}
                      className={cn(
                        'flex items-center justify-between py-2 px-2 -mx-2 rounded-md w-full text-left',
                        'hover:bg-[var(--surface-hover)]',
                        'transition-colors cursor-pointer'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <CategoryIcon
                          category={expense.category}
                          className="h-3.5 w-3.5 text-[var(--text-muted)] flex-shrink-0"
                        />
                        <span className="text-sm text-[var(--text-primary)] truncate">
                          {expense.expense_name}
                        </span>
                      </div>
                      <span className="text-sm font-medium text-[var(--text-primary)] ml-2">
                        {formatCurrency(expense.amount)}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Right sidebar backdrop - only on smaller screens */}
        {rightSidebarOpen && (
          <div
            className="fixed inset-0 bg-black/20 z-10 lg:hidden"
            onClick={() => setRightSidebarOpen(false)}
          />
        )}

        {/* Expense Detail Modal */}
        <ExpenseEditModal
          expense={selectedExpense}
          isOpen={selectedExpense !== null}
          onClose={() => setSelectedExpense(null)}
          onSave={handleSidebarExpenseSave}
          onDelete={handleSidebarExpenseDelete}
        />

        {/* Category Expenses Modal */}
        <CategoryExpensesModal
          category={selectedCategory}
          isOpen={selectedCategory !== null}
          onClose={() => setSelectedCategory(null)}
        />
    </div>
  )
}
