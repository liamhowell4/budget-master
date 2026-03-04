import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'
import type { ToolCallDoc } from '../types'
import { FloatingTooltip, TOOLTIP_WRAPPER } from './ChartTooltip'

interface Props {
  toolCalls: ToolCallDoc[]
  uidToName: Record<string, string>
}

const COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#3b82f6', '#84cc16',
]

export default function ToolUserBreakdown({ toolCalls, uidToName }: Props) {
  const { data, users } = useMemo(() => {
    // Count calls per tool per user
    const toolUserCounts: Record<string, Record<string, number>> = {}
    const toolUniqueUsers: Record<string, Set<string>> = {}

    for (const tc of toolCalls) {
      if (!toolUserCounts[tc.tool_name]) {
        toolUserCounts[tc.tool_name] = {}
        toolUniqueUsers[tc.tool_name] = new Set()
      }
      toolUserCounts[tc.tool_name][tc.uid] = (toolUserCounts[tc.tool_name][tc.uid] || 0) + 1
      toolUniqueUsers[tc.tool_name].add(tc.uid)
    }

    // Filter to tools with 3+ unique users for the stacked chart
    const qualifyingTools = Object.entries(toolUniqueUsers)
      .filter(([, uids]) => uids.size >= 3)
      .map(([name]) => name)

    // Sort by total calls descending
    qualifyingTools.sort((a, b) => {
      const totalA = Object.values(toolUserCounts[a]).reduce((s, v) => s + v, 0)
      const totalB = Object.values(toolUserCounts[b]).reduce((s, v) => s + v, 0)
      return totalB - totalA
    })

    // Collect all users that appear across qualifying tools
    const userSet = new Set<string>()
    for (const tool of qualifyingTools) {
      for (const uid of Object.keys(toolUserCounts[tool])) {
        userSet.add(uid)
      }
    }

    // Sort users by total calls across qualifying tools
    const userTotals: Record<string, number> = {}
    for (const uid of userSet) {
      userTotals[uid] = 0
      for (const tool of qualifyingTools) {
        userTotals[uid] += toolUserCounts[tool][uid] || 0
      }
    }
    const sortedUsers = [...userSet].sort((a, b) => userTotals[b] - userTotals[a])

    // Build chart data: each row is a tool, with a key per user
    const chartData = qualifyingTools.map((tool) => {
      const row: Record<string, string | number> = { tool }
      for (const uid of sortedUsers) {
        row[uid] = toolUserCounts[tool][uid] || 0
      }
      return row
    })

    return { data: chartData, users: sortedUsers }
  }, [toolCalls])

  const getName = (uid: string) => uidToName[uid] || uid.slice(0, 8)

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Tool Usage by User</h2>
        <p className="text-gray-600 text-sm">No tools with 3+ users found</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 overflow-visible">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-400">Tool Usage by User</h2>
        <p className="text-xs text-gray-600 mt-1">Tools with 3+ unique users</p>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(300, data.length * 40)} style={{ overflow: 'visible' }}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <YAxis dataKey="tool" type="category" width={160} tick={{ fill: '#d1d5db', fontSize: 12 }} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            wrapperStyle={TOOLTIP_WRAPPER}
            allowEscapeViewBox={{ x: true, y: true }}
            content={(props) => {
              const { active, payload, label, coordinate, viewBox } = props as any
              if (!active || !payload?.length) return null
              const activeEntries = (payload as any[]).filter((p: any) => (p.value as number) > 0)
              const total = activeEntries.reduce((s: number, p: any) => s + (p.value as number), 0)
              return (
                <FloatingTooltip active={active} coordinate={coordinate} viewBox={viewBox}>
                  <div style={{ fontWeight: 600, marginBottom: 3, fontSize: 11 }}>{label}</div>
                  {activeEntries.map((entry: any) => (
                    <div key={entry.dataKey} style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 1 }}>
                      <span style={{ width: 7, height: 7, borderRadius: '50%', background: entry.color, flexShrink: 0 }} />
                      <span style={{ color: '#d1d5db' }}>{getName(entry.dataKey)}</span>
                      <span style={{ marginLeft: 'auto', paddingLeft: 8, color: '#9ca3af' }}>{(entry.value as number).toLocaleString()}</span>
                    </div>
                  ))}
                  <div style={{ borderTop: '1px solid #374151', marginTop: 4, paddingTop: 4, display: 'flex', justifyContent: 'space-between', color: '#9ca3af', fontSize: 11 }}>
                    <span>{total.toLocaleString()} calls</span>
                    <span>{activeEntries.length} {activeEntries.length === 1 ? 'user' : 'users'}</span>
                  </div>
                </FloatingTooltip>
              )
            }}
          />
          <Legend formatter={(value) => getName(value)} />
          {users.map((uid, i) => (
            <Bar
              key={uid}
              dataKey={uid}
              stackId="1"
              fill={COLORS[i % COLORS.length]}
              name={uid}
              radius={i === users.length - 1 ? [0, 4, 4, 0] : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
