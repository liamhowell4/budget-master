import { useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { streamChat, sendExpense } from '@/services/chatService'
import { invalidateExpensesCache } from '@/hooks/useExpenses'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import type { ChatMessage, ChatEvent, ToolCall } from '@/types/chat'

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

        await streamChat(token, text, (event: ChatEvent) => {
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
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send message')
        // Remove the empty assistant message on error
        setMessages((prev) => prev.slice(0, -1))
      } finally {
        setIsLoading(false)
      }
    },
    [getToken, isLoading, addMessage, updateLastAssistantMessage]
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
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to process audio')
      } finally {
        setIsLoading(false)
      }
    },
    [getToken, isLoading, addMessage]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    sendAudio,
    clearMessages,
  }
}
