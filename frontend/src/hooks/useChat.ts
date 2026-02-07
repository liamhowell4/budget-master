import { useState, useCallback, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { streamChat, sendExpense } from '@/services/chatService'
import { invalidateExpensesCache } from '@/hooks/useExpenses'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import type { ChatMessage, ChatEvent, ToolCall, ConversationListItem } from '@/types/chat'
import {
  listConversations,
  getConversation,
  deleteConversation,
} from '@/services/conversationService'

// Tools that modify expense/budget data
const DATA_MODIFYING_TOOLS = [
  'save_expense',
  'update_expense',
  'delete_expense',
  'create_recurring_expense',
  'delete_recurring_expense',
]

export function useChat() {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Conversation state
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [conversationsLoading, setConversationsLoading] = useState(false)
  const conversationIdRef = useRef<string | null>(null)

  // Keep ref in sync with state
  conversationIdRef.current = currentConversationId

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message])
  }, [])

  const updateLastAssistantMessage = useCallback(
    (content: string, toolCalls?: ToolCall[]) => {
      setMessages((prev) => {
        const newMessages = [...prev]
        const lastIndex = newMessages.length - 1
        if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content,
            toolCalls,
          }
        }
        return newMessages
      })
    },
    []
  )

  // Load conversation list
  const loadConversations = useCallback(async () => {
    try {
      setConversationsLoading(true)
      const token = await getToken()
      if (!token) return

      const convList = await listConversations(token)
      setConversations(convList)
    } catch (err) {
      console.error('Failed to load conversations:', err)
    } finally {
      setConversationsLoading(false)
    }
  }, [getToken])

  // Load a specific conversation
  const loadConversation = useCallback(
    async (conversationId: string) => {
      try {
        setIsLoading(true)
        const token = await getToken()
        if (!token) return

        const conv = await getConversation(token, conversationId)
        setCurrentConversationId(conversationId)

        // Convert stored messages to ChatMessage format
        const loadedMessages: ChatMessage[] = conv.messages.map((msg, index) => ({
          id: `${conversationId}-${index}`,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          toolCalls: msg.tool_calls,
        }))
        setMessages(loadedMessages)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversation')
      } finally {
        setIsLoading(false)
      }
    },
    [getToken]
  )

  // Start a new conversation (clears messages and ID)
  const startNewConversation = useCallback(() => {
    setMessages([])
    setCurrentConversationId(null)
  }, [])

  // Delete a conversation
  const removeConversation = useCallback(
    async (conversationId: string) => {
      try {
        const token = await getToken()
        if (!token) return

        await deleteConversation(token, conversationId)

        // If we deleted the current conversation, start fresh
        if (currentConversationId === conversationId) {
          startNewConversation()
        }

        // Refresh the list
        await loadConversations()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete conversation')
      }
    },
    [getToken, currentConversationId, startNewConversation, loadConversations]
  )

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return

      setError(null)
      setIsLoading(true)

      // Add user message
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      }
      addMessage(userMessage)

      // Add placeholder assistant message
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        toolCalls: [],
      }
      addMessage(assistantMessage)

      try {
        const token = await getToken()
        if (!token) throw new Error('Not authenticated')

        let content = ''
        const toolCalls: ToolCall[] = []

        await streamChat({
          token,
          message: text,
          conversationId: conversationIdRef.current,
          onConversationId: (id) => {
            // Backend may return a new conversation_id if previous was stale
            setCurrentConversationId(id)
          },
          onEvent: (event: ChatEvent) => {
            if (event.type === 'tool_start') {
              toolCalls.push({
                id: event.id || crypto.randomUUID(),
                name: event.name || 'unknown',
                args: event.args,
              })
              updateLastAssistantMessage(content, [...toolCalls])
            } else if (event.type === 'tool_end') {
              // Update tool call with its result
              const toolIndex = toolCalls.findIndex((t) => t.id === event.id)
              if (toolIndex !== -1 && event.result !== undefined) {
                toolCalls[toolIndex].result = event.result
                updateLastAssistantMessage(content, [...toolCalls])
              }
              // Invalidate caches if a data-modifying tool completed
              if (event.name && DATA_MODIFYING_TOOLS.includes(event.name)) {
                invalidateExpensesCache()
                invalidateBudgetCache()
              }
            } else if (event.type === 'text') {
              content += event.content || ''
              updateLastAssistantMessage(content, toolCalls)
            }
          },
        })

        // Refresh conversation list after sending
        loadConversations()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send message')
        // Remove the empty assistant message on error
        setMessages((prev) => prev.slice(0, -1))
      } finally {
        setIsLoading(false)
      }
    },
    [getToken, isLoading, addMessage, updateLastAssistantMessage, loadConversations]
  )

  const sendAudio = useCallback(
    async (audio: Blob) => {
      if (isLoading) return

      setError(null)
      setIsLoading(true)

      // Add placeholder messages
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: '[Voice message]',
        timestamp: new Date(),
      }
      addMessage(userMessage)

      try {
        const token = await getToken()
        if (!token) throw new Error('Not authenticated')

        const result = await sendExpense(token, { audio })

        // Invalidate caches since audio likely created an expense
        invalidateExpensesCache()
        invalidateBudgetCache()

        const assistantMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: result.message,
          timestamp: new Date(),
        }
        addMessage(assistantMessage)

        // Refresh conversation list
        loadConversations()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to process audio')
      } finally {
        setIsLoading(false)
      }
    },
    [getToken, isLoading, addMessage, loadConversations]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    // Chat state
    messages,
    isLoading,
    error,
    sendMessage,
    sendAudio,
    clearMessages,

    // Conversation state
    conversations,
    currentConversationId,
    conversationsLoading,
    loadConversations,
    loadConversation,
    startNewConversation,
    removeConversation,
  }
}
