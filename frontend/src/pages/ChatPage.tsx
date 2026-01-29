import { useEffect, useRef, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatInput, ChatMessage } from '@/components/chat'
import { useChat } from '@/hooks/useChat'
import { useBudget, invalidateBudgetCache } from '@/hooks/useBudget'
import { useExpenses, invalidateExpensesCache } from '@/hooks/useExpenses'
import { deleteExpense, updateExpense } from '@/services/expenseService'
import { formatConversationTitle } from '@/services/conversationService'
import { useServer } from '@/contexts/ServerContext'
import { Card, ProgressBar, Spinner, CategoryIcon, Modal } from '@/components/ui'
import { cn } from '@/utils/cn'
import { formatCurrency, formatExpenseDate } from '@/utils/formatters'
import {
  PanelRightClose,
  PanelRight,
  PanelLeftClose,
  PanelLeft,
  RefreshCw,
  Calendar,
  Clock,
  Repeat,
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
          <div className="text-center p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Spent</p>
            <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {formatCurrency(category.spending)}
            </p>
          </div>
          <div className="text-center p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Budget</p>
            <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {formatCurrency(category.cap)}
            </p>
          </div>
          <div className="text-center p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Remaining</p>
            <p
              className={cn(
                'text-lg font-semibold',
                category.remaining >= 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-red-600 dark:text-red-400'
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
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            {stats ? `${stats.count} expense${stats.count !== 1 ? 's' : ''}` : 'No expenses'}
          </p>
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className={cn(
                'appearance-none pl-8 pr-3 py-1.5 rounded-md text-xs',
                'bg-neutral-100 dark:bg-neutral-800',
                'border border-neutral-200 dark:border-neutral-700',
                'text-neutral-700 dark:text-neutral-300',
                'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600',
                'cursor-pointer'
              )}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400 pointer-events-none" />
          </div>
        </div>

        {/* Expense list */}
        {loading ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : sortedExpenses.length === 0 ? (
          <div className="text-center py-8 text-sm text-neutral-500 dark:text-neutral-400">
            No expenses in this category
          </div>
        ) : (
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {sortedExpenses.map((expense) => (
              <div
                key={expense.id}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg',
                  'bg-neutral-50 dark:bg-neutral-800'
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                    {expense.expense_name}
                  </p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500">
                    {formatExpenseDate(expense.date)}
                  </p>
                </div>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 ml-3">
                  {formatCurrency(expense.amount)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Average spending */}
        {stats && stats.count > 1 && (
          <div className="pt-3 border-t border-neutral-200 dark:border-neutral-800">
            <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center">
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
  } = useChat()
  const { budget } = useBudget()
  const { expenses } = useExpenses()
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
      // Invalidate caches so sidebar and other views update
      invalidateExpensesCache()
      invalidateBudgetCache()
    } catch (err) {
      console.error('Failed to delete expense:', err)
    }
  }

  const handleExpenseEdit = async (expenseId: string, updates: { name?: string; amount?: number }) => {
    try {
      await updateExpense(expenseId, {
        expense_name: updates.name,
        amount: updates.amount,
      })
      // Invalidate caches so sidebar and other views update
      invalidateExpensesCache()
      invalidateBudgetCache()
    } catch (err) {
      console.error('Failed to update expense:', err)
    }
  }

  const activeCategories = budget?.categories.filter((cat) => cat.cap > 0).slice(0, 4) || []

  return (
    <div className="flex h-[calc(100dvh-56px)]">
        {/* Left sidebar - Conversation History */}
        <aside
          className={cn(
            'w-64 border-r border-neutral-200 dark:border-neutral-800',
            'bg-neutral-50 dark:bg-neutral-900 overflow-y-auto',
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
                'bg-white dark:bg-neutral-800',
                'border border-neutral-200 dark:border-neutral-700',
                'text-neutral-700 dark:text-neutral-200',
                'hover:bg-neutral-100 dark:hover:bg-neutral-700',
                'transition-colors text-sm font-medium'
              )}
            >
              <Plus className="h-4 w-4" />
              New Chat
            </button>

            {/* Conversation List */}
            <div className="pt-2">
              <h3 className="px-2 text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2">
                Recent
              </h3>
              {conversationsLoading ? (
                <div className="flex justify-center py-4">
                  <Spinner size="sm" />
                </div>
              ) : conversations.length === 0 ? (
                <p className="px-2 text-xs text-neutral-400 dark:text-neutral-500">
                  No conversations yet
                </p>
              ) : (
                <div className="space-y-1">
                  {conversations.map((conv) => (
                    <div
                      key={conv.conversation_id}
                      className={cn(
                        'group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer',
                        'hover:bg-white dark:hover:bg-neutral-800',
                        'transition-colors',
                        currentConversationId === conv.conversation_id &&
                          'bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700'
                      )}
                      onClick={() => loadConversation(conv.conversation_id)}
                    >
                      <MessageSquare className="h-4 w-4 text-neutral-400 dark:text-neutral-500 flex-shrink-0" />
                      <span className="flex-1 text-sm text-neutral-700 dark:text-neutral-300 truncate">
                        {formatConversationTitle(conv)}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          removeConversation(conv.conversation_id)
                        }}
                        className={cn(
                          'opacity-0 group-hover:opacity-100',
                          'p-1 rounded hover:bg-neutral-200 dark:hover:bg-neutral-700',
                          'text-neutral-400 hover:text-red-500 dark:hover:text-red-400',
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
                    <h2 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-1">
                      Track your expenses
                    </h2>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
                      Start a conversation to log and manage your spending
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {['Coffee $5', 'Lunch $15', 'Groceries $80'].map((example) => (
                        <button
                          key={example}
                          onClick={() => sendMessage(example)}
                          className={cn(
                            'px-3 py-1.5 rounded-md text-sm',
                            'bg-neutral-100 dark:bg-neutral-800',
                            'border border-neutral-200 dark:border-neutral-700',
                            'text-neutral-600 dark:text-neutral-300',
                            'hover:bg-neutral-200 dark:hover:bg-neutral-700',
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
                      onExpenseDelete={handleExpenseDelete}
                      onExpenseEdit={handleExpenseEdit}
                    />
                  ))}

                  {isLoading && messages[messages.length - 1]?.content === '' && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
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
                <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
                  <Spinner size="sm" />
                  <span>Connecting to server...</span>
                </div>
              )}
              {serverError && !isConnecting && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-amber-600 dark:text-amber-400">{serverError}</p>
                  <button
                    onClick={reconnect}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm',
                      'bg-neutral-100 dark:bg-neutral-800',
                      'text-neutral-600 dark:text-neutral-300',
                      'hover:bg-neutral-200 dark:hover:bg-neutral-700',
                      'transition-colors'
                    )}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry
                  </button>
                </div>
              )}
              {error && !serverError && (
                <p className="text-sm text-red-500">{error}</p>
              )}
            </div>
          )}

          {/* Chat input */}
          <div className="border-t border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950">
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
            'bg-white dark:bg-neutral-800',
            'border border-neutral-200 dark:border-neutral-700',
            'text-neutral-600 dark:text-neutral-300',
            'hover:bg-neutral-50 dark:hover:bg-neutral-700',
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
            'bg-white dark:bg-neutral-800',
            'border border-neutral-200 dark:border-neutral-700',
            'text-neutral-600 dark:text-neutral-300',
            'hover:bg-neutral-50 dark:hover:bg-neutral-700',
            'transition-colors'
          )}
          aria-label={rightSidebarOpen ? 'Close budget' : 'Open budget'}
        >
          {rightSidebarOpen ? <PanelRightClose className="h-5 w-5" /> : <PanelRight className="h-5 w-5" />}
        </button>

        {/* Right sidebar */}
        <aside
          className={cn(
            'w-80 border-l border-neutral-200 dark:border-neutral-800',
            'bg-white dark:bg-neutral-950 overflow-y-auto',
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
                <h3 className="text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-3">
                  {budget.month_name}
                </h3>
                <button
                  onClick={() => navigate('/dashboard')}
                  className="w-full text-left"
                >
                  <Card padding="sm" hover>
                    <div className="space-y-3">
                      <div className="flex items-baseline justify-between">
                        <span className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight">
                          {formatCurrency(budget.total_remaining)}
                        </span>
                        <span className="text-xs text-neutral-500 dark:text-neutral-400">
                          remaining
                        </span>
                      </div>
                      <ProgressBar percentage={budget.total_percentage} />
                      <div className="flex justify-between text-xs text-neutral-400 dark:text-neutral-500">
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
                <h3 className="text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-3">
                  Categories
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
                          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-neutral-100 dark:bg-neutral-800">
                            <CategoryIcon
                              category={cat.category}
                              className="h-4 w-4 text-neutral-500 dark:text-neutral-400"
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                                {CATEGORY_LABELS[cat.category] || cat.category}
                              </span>
                              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                                {cat.percentage.toFixed(0)}%
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
                <h3 className="text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-3">
                  Recent
                </h3>
                <div className="space-y-1">
                  {expenses.slice(0, 5).map((expense) => (
                    <button
                      key={expense.id}
                      onClick={() => setSelectedExpense(expense)}
                      className={cn(
                        'flex items-center justify-between py-2 px-2 -mx-2 rounded-md w-full text-left',
                        'hover:bg-neutral-50 dark:hover:bg-neutral-900',
                        'transition-colors cursor-pointer'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <CategoryIcon
                          category={expense.category}
                          className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500 flex-shrink-0"
                        />
                        <span className="text-sm text-neutral-900 dark:text-neutral-100 truncate">
                          {expense.expense_name}
                        </span>
                      </div>
                      <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100 ml-2">
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
        {selectedExpense && (
          <Modal
            isOpen={selectedExpense !== null}
            onClose={() => setSelectedExpense(null)}
            title="Expense Details"
          >
            <div className="space-y-6">
              {/* Amount - large display */}
              <div className="text-center py-4">
                <p className="text-4xl font-semibold text-neutral-900 dark:text-neutral-100">
                  {formatCurrency(selectedExpense.amount)}
                </p>
              </div>

              {/* Details */}
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
                    <CategoryIcon
                      category={selectedExpense.category}
                      className="h-5 w-5 text-neutral-600 dark:text-neutral-300"
                    />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">Category</p>
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {CATEGORY_LABELS[selectedExpense.category] || selectedExpense.category}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
                    <Calendar className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">Date</p>
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {formatExpenseDate(selectedExpense.date)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neutral-200 dark:bg-neutral-700">
                    {selectedExpense.input_type === 'recurring' ? (
                      <Repeat className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
                    ) : (
                      <Clock className="h-5 w-5 text-neutral-600 dark:text-neutral-300" />
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">Description</p>
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {selectedExpense.expense_name}
                    </p>
                    {selectedExpense.input_type && (
                      <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
                        {selectedExpense.input_type === 'recurring' ? 'Recurring expense' : 'Manual entry'}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </Modal>
        )}

        {/* Category Expenses Modal */}
        <CategoryExpensesModal
          category={selectedCategory}
          isOpen={selectedCategory !== null}
          onClose={() => setSelectedCategory(null)}
        />
    </div>
  )
}
