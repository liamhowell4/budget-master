import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  listConversations,
  getConversation,
  createConversation,
  deleteConversation,
  isConversationActive,
} from '@/services/conversationService'
import type { ConversationListItem, ChatMessage } from '@/types/chat'

export function useConversations() {
  const { getToken } = useAuth()
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load conversation list
  const loadConversations = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const token = await getToken()
      if (!token) return

      const convList = await listConversations(token)
      setConversations(convList)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations')
    } finally {
      setIsLoading(false)
    }
  }, [getToken])

  // Load a specific conversation and return its messages
  const loadConversation = useCallback(
    async (conversationId: string): Promise<ChatMessage[]> => {
      try {
        const token = await getToken()
        if (!token) return []

        const conv = await getConversation(token, conversationId)
        setCurrentConversationId(conversationId)

        // Convert stored messages to ChatMessage format
        return conv.messages.map((msg, index) => ({
          id: `${conversationId}-${index}`,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
        }))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversation')
        return []
      }
    },
    [getToken]
  )

  // Start a new conversation or continue the most recent active one
  const getOrCreateActiveConversation = useCallback(async (): Promise<string> => {
    try {
      const token = await getToken()
      if (!token) throw new Error('Not authenticated')

      // Check if there's a recent active conversation
      const convList = await listConversations(token, 1)

      if (convList.length > 0 && isConversationActive(convList[0].last_activity)) {
        // Continue the existing active conversation
        setCurrentConversationId(convList[0].conversation_id)
        return convList[0].conversation_id
      }

      // Create a new conversation
      const newId = await createConversation(token)
      setCurrentConversationId(newId)

      // Refresh the conversation list
      await loadConversations()

      return newId
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation')
      throw err
    }
  }, [getToken, loadConversations])

  // Start a fresh new conversation (user explicitly wants new chat)
  const startNewConversation = useCallback(async (): Promise<string> => {
    try {
      const token = await getToken()
      if (!token) throw new Error('Not authenticated')

      const newId = await createConversation(token)
      setCurrentConversationId(newId)

      // Refresh the conversation list
      await loadConversations()

      return newId
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation')
      throw err
    }
  }, [getToken, loadConversations])

  // Delete a conversation
  const removeConversation = useCallback(
    async (conversationId: string) => {
      try {
        const token = await getToken()
        if (!token) return

        await deleteConversation(token, conversationId)

        // If we deleted the current conversation, clear it
        if (currentConversationId === conversationId) {
          setCurrentConversationId(null)
        }

        // Refresh the list
        await loadConversations()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete conversation')
      }
    },
    [getToken, currentConversationId, loadConversations]
  )

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  return {
    conversations,
    currentConversationId,
    isLoading,
    error,
    loadConversations,
    loadConversation,
    getOrCreateActiveConversation,
    startNewConversation,
    removeConversation,
    setCurrentConversationId,
  }
}
