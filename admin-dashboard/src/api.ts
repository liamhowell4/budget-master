import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL as string
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY as string

const client = axios.create({
  baseURL: API_URL,
  headers: { 'X-API-Key': ADMIN_API_KEY },
})

export async function fetchUsers() {
  const res = await client.get('/admin/users')
  return res.data
}

export async function fetchAnalytics(days: number) {
  const res = await client.get(`/admin/analytics?days=${days}`)
  return res.data
}

export async function streamChat(
  message: string,
  history: { role: string; content: string }[],
  context: object,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${API_URL}/admin/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': ADMIN_API_KEY,
    },
    body: JSON.stringify({ message, history, context }),
  })

  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`)

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = JSON.parse(line.slice(6))
      if (payload.text) onChunk(payload.text)
      if (payload.done) return
      if (payload.error) throw new Error(payload.error)
    }
  }
}
