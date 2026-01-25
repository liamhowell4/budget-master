import { API_URL } from '@/utils/constants'

export interface Server {
  id: string
  name: string
  description: string
}

export interface ServerStatus {
  connected: boolean
  server_id: string | null
  server_name: string | null
}

export async function getServers(token: string): Promise<Server[]> {
  const response = await fetch(`${API_URL}/servers`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch servers: ${response.statusText}`)
  }

  const data = await response.json()
  // Backend returns array directly, not { servers: [...] }
  return Array.isArray(data) ? data : (data.servers || [])
}

export async function connectToServer(token: string, serverId: string): Promise<void> {
  const response = await fetch(`${API_URL}/connect/${serverId}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to connect to server: ${response.statusText}`)
  }
}

export async function getServerStatus(token: string): Promise<ServerStatus> {
  const response = await fetch(`${API_URL}/status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to get server status: ${response.statusText}`)
  }

  return response.json()
}

export async function disconnectFromServer(token: string): Promise<void> {
  const response = await fetch(`${API_URL}/disconnect`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to disconnect: ${response.statusText}`)
  }
}
