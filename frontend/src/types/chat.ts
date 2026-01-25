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
