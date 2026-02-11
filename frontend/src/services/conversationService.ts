import { API_URL } from '@/utils/constants'
import type { Conversation, ConversationListItem } from '@/types/chat'

export async function listConversations(token: string, limit = 20): Promise<ConversationListItem[]> {
  const response = await fetch(`${API_URL}/conversations?limit=${limit}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to list conversations: ${response.statusText}`)
  }

  const data = await response.json()
  const conversations = data.conversations || []

  // Transform to include message count and first message preview
  return conversations.map((conv: Conversation) => ({
    conversation_id: conv.conversation_id,
    created_at: conv.created_at,
    last_activity: conv.last_activity,
    summary: conv.summary,
    message_count: conv.messages?.length || 0,
    first_message: conv.messages?.[0]?.content?.slice(0, 50) || undefined,
  }))
}

export async function getConversation(token: string, conversationId: string): Promise<Conversation> {
  const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to get conversation: ${response.statusText}`)
  }

  return response.json()
}

export async function createConversation(token: string): Promise<string> {
  const response = await fetch(`${API_URL}/conversations`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to create conversation: ${response.statusText}`)
  }

  const data = await response.json()
  return data.conversation_id
}

export async function deleteConversation(token: string, conversationId: string): Promise<void> {
  const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.statusText}`)
  }
}

export async function markExpenseDeleted(
  token: string,
  conversationId: string,
  expenseId: string
): Promise<void> {
  const response = await fetch(`${API_URL}/conversations/${conversationId}/deleted-expenses`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ expense_id: expenseId }),
  })

  if (!response.ok) {
    throw new Error(`Failed to mark expense as deleted: ${response.statusText}`)
  }
}

// Check if a conversation is still "active" (within 12 hours of last activity)
export function isConversationActive(lastActivity: string): boolean {
  const INACTIVITY_THRESHOLD_HOURS = 12
  const lastActivityDate = new Date(lastActivity)
  const now = new Date()
  const hoursSinceActivity = (now.getTime() - lastActivityDate.getTime()) / (1000 * 60 * 60)
  return hoursSinceActivity < INACTIVITY_THRESHOLD_HOURS
}

// Format conversation title from date and first message
export function formatConversationTitle(conv: ConversationListItem): string {
  const date = new Date(conv.last_activity || conv.created_at)
  const dateStr = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
  const timeStr = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })

  if (conv.first_message) {
    const preview = conv.first_message.length > 30
      ? conv.first_message.slice(0, 30) + '...'
      : conv.first_message
    return `${dateStr} - ${preview}`
  }

  return `${dateStr}, ${timeStr}`
}
