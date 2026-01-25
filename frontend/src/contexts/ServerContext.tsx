import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { getServers, connectToServer, getServerStatus, type ServerStatus } from '@/services/serverService'

interface ServerContextType {
  isConnected: boolean
  isConnecting: boolean
  serverName: string | null
  error: string | null
  reconnect: () => Promise<void>
}

const ServerContext = createContext<ServerContextType | null>(null)

export function ServerProvider({ children }: { children: ReactNode }) {
  const { user, getToken } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [serverName, setServerName] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasAttempted = useRef(false)

  const connect = useCallback(async () => {
    if (!user || isConnecting) return

    setIsConnecting(true)
    setError(null)

    try {
      const token = await getToken()
      if (!token) throw new Error('Not authenticated')

      // Check if already connected
      try {
        const status: ServerStatus = await getServerStatus(token)
        if (status.connected) {
          setIsConnected(true)
          setServerName(status.server_name)
          setIsConnecting(false)
          return
        }
      } catch {
        // Status check failed, try to connect
      }

      // Get available servers
      const servers = await getServers(token)
      if (servers.length === 0) {
        throw new Error('No MCP servers available')
      }

      // Connect to the first server (usually 'expense_tracker')
      const server = servers[0]
      await connectToServer(token, server.id)

      setIsConnected(true)
      setServerName(server.name)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect to server'
      setError(message)
      setIsConnected(false)
      console.error('Server connection error:', err)
    } finally {
      setIsConnecting(false)
    }
  }, [user, getToken, isConnecting])

  // Auto-connect when user logs in (only once)
  useEffect(() => {
    if (user && !hasAttempted.current) {
      hasAttempted.current = true
      connect()
    }
  }, [user, connect])

  // Reset state when user logs out
  useEffect(() => {
    if (!user) {
      setIsConnected(false)
      setServerName(null)
      setError(null)
      hasAttempted.current = false
    }
  }, [user])

  const reconnect = useCallback(async () => {
    hasAttempted.current = true
    await connect()
  }, [connect])

  return (
    <ServerContext.Provider
      value={{
        isConnected,
        isConnecting,
        serverName,
        error,
        reconnect,
      }}
    >
      {children}
    </ServerContext.Provider>
  )
}

export function useServer() {
  const context = useContext(ServerContext)
  if (!context) {
    throw new Error('useServer must be used within a ServerProvider')
  }
  return context
}
