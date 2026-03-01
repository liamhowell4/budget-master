import { useMemo, useState } from 'react'
import type { TokenUsageDoc, ToolCallDoc } from '../types'

interface Props {
  tokenUsage: TokenUsageDoc[]
  toolCalls: ToolCallDoc[]
  uidToName: Record<string, string>
}

interface UserRow {
  uid: string
  name: string
  calls: number
  tokensIn: number
  tokensOut: number
  topTool: string
  lastActive: string
}

type SortKey = keyof UserRow

export default function UserTable({ tokenUsage, toolCalls, uidToName }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('calls')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const rows = useMemo((): UserRow[] => {
    const byUid: Record<string, UserRow> = {}
    for (const doc of tokenUsage) {
      const uid = doc.uid
      if (!byUid[uid]) {
        byUid[uid] = { uid, name: uidToName[uid] || uid, calls: 0, tokensIn: 0, tokensOut: 0, topTool: '—', lastActive: '' }
      }
      byUid[uid].calls += 1
      byUid[uid].tokensIn += doc.input_tokens || 0
      byUid[uid].tokensOut += doc.output_tokens || 0
      if (doc.timestamp && doc.timestamp > byUid[uid].lastActive) {
        byUid[uid].lastActive = doc.timestamp
      }
    }

    // Compute top tool per user
    const toolByUid: Record<string, Record<string, number>> = {}
    for (const tc of toolCalls) {
      if (!toolByUid[tc.uid]) toolByUid[tc.uid] = {}
      toolByUid[tc.uid][tc.tool_name] = (toolByUid[tc.uid][tc.tool_name] || 0) + 1
    }
    for (const uid of Object.keys(byUid)) {
      const tools = toolByUid[uid]
      if (tools) {
        byUid[uid].topTool = Object.entries(tools).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—'
      }
    }

    return Object.values(byUid)
  }, [tokenUsage, toolCalls, uidToName])

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (typeof av === 'number' && typeof bv === 'number') {
        return sortDir === 'desc' ? bv - av : av - bv
      }
      return sortDir === 'desc'
        ? String(bv).localeCompare(String(av))
        : String(av).localeCompare(String(bv))
    })
  }, [rows, sortKey, sortDir])

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const cols: { key: SortKey; label: string }[] = [
    { key: 'name', label: 'User' },
    { key: 'calls', label: 'API Calls' },
    { key: 'tokensIn', label: 'Tokens In' },
    { key: 'tokensOut', label: 'Tokens Out' },
    { key: 'topTool', label: 'Top Tool' },
    { key: 'lastActive', label: 'Last Active' },
  ]

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-5 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400">Usage by User</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {cols.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="text-left px-4 py-3 text-gray-500 font-medium cursor-pointer hover:text-gray-300 select-none"
                >
                  {col.label} {sortKey === col.key ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.uid} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 text-white font-medium">{row.name}</td>
                <td className="px-4 py-3 text-gray-300">{row.calls.toLocaleString()}</td>
                <td className="px-4 py-3 text-gray-300">{row.tokensIn.toLocaleString()}</td>
                <td className="px-4 py-3 text-gray-300">{row.tokensOut.toLocaleString()}</td>
                <td className="px-4 py-3 text-indigo-400">{row.topTool}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {row.lastActive ? row.lastActive.slice(0, 10) : '—'}
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-600">No data</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
