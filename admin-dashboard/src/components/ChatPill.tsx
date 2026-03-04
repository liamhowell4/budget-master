import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { streamChat } from '../api'
import type { AnalyticsSummary, TokenUsageDoc, ToolCallDoc } from '../types'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
}

interface ChatHistory {
  chats: ChatSession[]
  activeId: string | null
}

const STORAGE_KEY = 'admin-chat-history'

function loadHistory(): ChatHistory {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { chats: [], activeId: null }
}

function saveHistory(history: ChatHistory) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

interface ChatPillProps {
  summary: AnalyticsSummary | null
  tokenUsage: TokenUsageDoc[]
  toolCalls: ToolCallDoc[]
}

function buildAggregateContext(
  summary: AnalyticsSummary | null,
  tokenUsage: TokenUsageDoc[],
  toolCalls: ToolCallDoc[],
) {
  const byDate: Record<string, { input_tokens: number; output_tokens: number; count: number }> = {}
  for (const doc of tokenUsage) {
    const date = doc.timestamp?.slice(0, 10) || 'unknown'
    if (!byDate[date]) byDate[date] = { input_tokens: 0, output_tokens: 0, count: 0 }
    byDate[date].input_tokens += doc.input_tokens
    byDate[date].output_tokens += doc.output_tokens
    byDate[date].count += 1
  }

  const byTool: Record<string, number> = {}
  for (const doc of toolCalls) {
    byTool[doc.tool_name] = (byTool[doc.tool_name] || 0) + 1
  }

  const byEndpoint: Record<string, number> = {}
  for (const doc of tokenUsage) {
    byEndpoint[doc.endpoint] = (byEndpoint[doc.endpoint] || 0) + 1
  }

  return {
    summary,
    daily_totals: Object.entries(byDate)
      .map(([date, v]) => ({ date, ...v }))
      .sort((a, b) => a.date.localeCompare(b.date)),
    tool_usage: Object.entries(byTool)
      .map(([tool_name, count]) => ({ tool_name, count }))
      .sort((a, b) => b.count - a.count),
    endpoint_usage: Object.entries(byEndpoint)
      .map(([endpoint, count]) => ({ endpoint, count }))
      .sort((a, b) => b.count - a.count),
  }
}

export default function ChatPill({ summary, tokenUsage, toolCalls }: ChatPillProps) {
  const [history, setHistory] = useState<ChatHistory>(loadHistory)
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [showMessages, setShowMessages] = useState(false)
  const [showList, setShowList] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const activeChat = useMemo(
    () => history.chats.find((c) => c.id === history.activeId) ?? null,
    [history],
  )
  const messages = activeChat?.messages ?? []

  const context = useMemo(
    () => buildAggregateContext(summary, tokenUsage, toolCalls),
    [summary, tokenUsage, toolCalls],
  )

  // Persist history to localStorage
  const persistHistory = useCallback((h: ChatHistory) => {
    setHistory(h)
    saveHistory(h)
  }, [])

  // Auto-scroll on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Click-outside to dismiss
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowMessages(false)
        setShowList(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [])

  const handleOpenCard = () => {
    if (activeChat && activeChat.messages.length > 0) {
      setShowList(false)
      setShowMessages(true)
    } else if (history.chats.length > 0) {
      setShowList(true)
      setShowMessages(true)
    } else {
      // No chats yet — just open so card is visible when first message sent
      setShowList(false)
      setShowMessages(true)
    }
  }

  const createNewChat = useCallback((): string => {
    const id = crypto.randomUUID()
    const session: ChatSession = { id, title: 'New chat', messages: [], createdAt: Date.now() }
    const next = { chats: [session, ...history.chats], activeId: id }
    persistHistory(next)
    return id
  }, [history, persistHistory])

  const handleNewChat = () => {
    createNewChat()
    setShowList(false)
    setShowMessages(true)
  }

  const handleSelectChat = (id: string) => {
    persistHistory({ ...history, activeId: id })
    setShowList(false)
    setShowMessages(true)
  }

  const handleDeleteChat = (id: string) => {
    const next = {
      chats: history.chats.filter((c) => c.id !== id),
      activeId: history.activeId === id ? null : history.activeId,
    }
    persistHistory(next)
    if (next.chats.length === 0) {
      setShowMessages(false)
      setShowList(false)
    }
  }

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    // Ensure we have an active chat
    let currentHistory = history
    let chatId = currentHistory.activeId
    if (!chatId || !currentHistory.chats.find((c) => c.id === chatId)) {
      const id = crypto.randomUUID()
      const session: ChatSession = { id, title: text.slice(0, 40), messages: [], createdAt: Date.now() }
      currentHistory = { chats: [session, ...currentHistory.chats], activeId: id }
      chatId = id
    }

    const chat = currentHistory.chats.find((c) => c.id === chatId)!
    const userMsg: ChatMessage = { role: 'user', content: text }
    const assistantMsg: ChatMessage = { role: 'assistant', content: '' }
    const updatedMessages = [...chat.messages, userMsg, assistantMsg]

    // Set title from first user message
    const title = chat.messages.length === 0 ? text.slice(0, 40) : chat.title

    const nextChats = currentHistory.chats.map((c) =>
      c.id === chatId ? { ...c, messages: updatedMessages, title } : c,
    )
    const nextHistory = { chats: nextChats, activeId: chatId }
    persistHistory(nextHistory)

    setInput('')
    setIsStreaming(true)
    setShowMessages(true)
    setShowList(false)

    const prevMessages = chat.messages.map((m) => ({ role: m.role, content: m.content }))

    try {
      await streamChat(text, prevMessages, context, (chunk) => {
        setHistory((prev) => {
          const chats = prev.chats.map((c) => {
            if (c.id !== chatId) return c
            const msgs = [...c.messages]
            const last = msgs[msgs.length - 1]
            msgs[msgs.length - 1] = { ...last, content: last.content + chunk }
            return { ...c, messages: msgs }
          })
          return { ...prev, chats }
        })
      })
    } catch (err) {
      setHistory((prev) => {
        const chats = prev.chats.map((c) => {
          if (c.id !== chatId) return c
          const msgs = [...c.messages]
          msgs[msgs.length - 1] = {
            role: 'assistant',
            content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
          }
          return { ...c, messages: msgs }
        })
        return { ...prev, chats }
      })
    } finally {
      setIsStreaming(false)
      // Persist final state
      setHistory((prev) => {
        saveHistory(prev)
        return prev
      })
    }
  }, [input, isStreaming, history, context, persistHistory])

  const cardVisible = showMessages

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 560,
        maxWidth: 'calc(100vw - 48px)',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        pointerEvents: 'none',
      }}
    >
      {/* Clip wrapper — clips the card as it slides behind the pill */}
      <div
        style={{
          overflow: 'hidden',
          paddingTop: 420,
          marginTop: -420,
          pointerEvents: 'none',
        }}
      >
        {/* Message card — slides up from behind the pill */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.92)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid #334155',
            borderRadius: 20,
            marginBottom: 10,
            maxHeight: 400,
            display: 'flex',
            flexDirection: 'column',
            transition: 'transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease',
            transform: cardVisible ? 'translateY(0)' : 'translateY(calc(100% + 24px))',
            opacity: cardVisible ? 1 : 0,
            pointerEvents: cardVisible ? 'auto' : 'none',
          }}
        >
        {/* Toolbar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px',
            borderBottom: '1px solid #1e293b',
            flexShrink: 0,
          }}
        >
          {!showList && activeChat && activeChat.messages.length > 0 ? (
            <button
              onClick={() => setShowList(true)}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: 13,
                cursor: 'pointer',
                padding: '2px 6px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#e2e8f0')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
            >
              ← Chats
            </button>
          ) : (
            <span style={{ fontSize: 12, color: '#64748b', fontWeight: 600, letterSpacing: 0.5 }}>
              {showList ? 'CHAT HISTORY' : 'CHAT'}
            </span>
          )}
          <button
            onClick={handleNewChat}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              fontSize: 13,
              cursor: 'pointer',
              padding: '2px 6px',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#e2e8f0')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            + New
          </button>
        </div>

        {/* Content area */}
        <div
          ref={scrollRef}
          style={{
            overflowY: 'auto',
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            flex: 1,
          }}
        >
          {showList ? (
            // Chat list view
            history.chats.length === 0 ? (
              <div style={{ color: '#64748b', fontSize: 13, textAlign: 'center', padding: 20 }}>
                No chats yet. Type a question below to start.
              </div>
            ) : (
              history.chats.map((chat) => (
                <div
                  key={chat.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 4px',
                    borderBottom: '1px solid #1e293b',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleSelectChat(chat.id)}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(51, 65, 85, 0.4)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        color: '#e2e8f0',
                        fontSize: 13,
                        fontWeight: 500,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {chat.title}
                    </div>
                    <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>
                      {relativeTime(chat.createdAt)} · {chat.messages.filter((m) => m.role === 'user').length} messages
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteChat(chat.id)
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#475569',
                      fontSize: 14,
                      cursor: 'pointer',
                      padding: '2px 6px',
                      flexShrink: 0,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                    onMouseLeave={(e) => (e.currentTarget.style.color = '#475569')}
                  >
                    ×
                  </button>
                </div>
              ))
            )
          ) : (
            // Conversation view
            <>
              {messages.length === 0 ? (
                <div style={{ color: '#64748b', fontSize: 13, textAlign: 'center', padding: 20 }}>
                  Ask a question about your usage data.
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 14,
                      lineHeight: 1.6,
                      paddingTop: i > 0 ? 12 : 0,
                      borderTop: i > 0 ? '1px solid #1e293b' : 'none',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        textTransform: 'uppercase' as const,
                        letterSpacing: 0.5,
                        marginBottom: 3,
                        color: msg.role === 'user' ? '#60a5fa' : '#a78bfa',
                      }}
                    >
                      {msg.role === 'user' ? 'You' : 'Assistant'}
                    </div>
                    <div style={{ color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                      {msg.content || (isStreaming && i === messages.length - 1 ? '...' : '')}
                    </div>
                  </div>
                ))
              )}
            </>
          )}
        </div>
        </div>
      </div>

      {/* Pill input — sits on top so card slides from behind it */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          alignItems: 'center',
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: 9999,
          padding: '4px 6px 4px 20px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          pointerEvents: 'auto',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={handleOpenCard}
          onClick={handleOpenCard}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Ask about your usage data..."
          disabled={isStreaming}
          style={{
            flex: 1,
            background: 'none',
            border: 'none',
            outline: 'none',
            color: '#e2e8f0',
            fontSize: 14,
            padding: '12px 0',
          }}
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            border: 'none',
            color: 'white',
            width: 38,
            height: 38,
            borderRadius: '50%',
            cursor: isStreaming || !input.trim() ? 'default' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            opacity: isStreaming || !input.trim() ? 0.5 : 1,
            transition: 'opacity 0.2s',
          }}
        >
          ↑
        </button>
      </div>
    </div>
  )
}
