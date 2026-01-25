import { API_URL } from '@/utils/constants'
import type { ChatEvent } from '@/types/chat'

export async function streamChat(
  token: string,
  message: string,
  onEvent: (event: ChatEvent) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  })

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') return
        if (data.startsWith('[ERROR]')) {
          throw new Error(data.slice(7))
        }
        try {
          const event = JSON.parse(data) as ChatEvent
          onEvent(event)
        } catch {
          // Non-JSON text chunk
          if (data.trim()) {
            onEvent({ type: 'text', content: data })
          }
        }
      }
    }
  }
}

export async function sendExpense(
  token: string,
  options: { text?: string; audio?: Blob }
): Promise<{ success: boolean; message: string }> {
  const formData = new FormData()

  if (options.text) {
    formData.append('text', options.text)
  }

  if (options.audio) {
    formData.append('audio', options.audio, 'recording.webm')
  }

  const response = await fetch(`${API_URL}/mcp/process_expense`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.statusText}`)
  }

  return response.json()
}
