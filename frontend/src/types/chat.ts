export interface ToolCall {
  id: string
  name: string
  args?: Record<string, unknown>
  result?: unknown
}

export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  toolCalls?: ToolCall[]
  timestamp: Date
}

export type ChatEventType = 'tool_start' | 'tool_end' | 'text'

export interface ChatEvent {
  type: ChatEventType
  id?: string
  name?: string
  args?: Record<string, unknown>
  content?: string
  result?: unknown
}

// Conversation types for persistent chat history
export interface StoredMessage {
  role: MessageRole
  content: string
  timestamp: string
  tool_calls?: ToolCall[]
}

export interface Conversation {
  conversation_id: string
  created_at: string
  last_activity: string
  messages: StoredMessage[]
  summary: string | null
  recent_expenses: Array<{
    expense_id: string
    expense_name: string
    amount: number
    category: string
    timestamp: string
  }>
  deleted_expense_ids?: string[]
}

export interface ConversationListItem {
  conversation_id: string
  created_at: string
  last_activity: string
  summary: string | null
  message_count: number
  first_message?: string
}
