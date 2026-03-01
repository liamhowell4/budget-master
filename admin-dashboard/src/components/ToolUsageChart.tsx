import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import type { ToolCallDoc } from '../types'

interface Props {
  toolCalls: ToolCallDoc[]
}

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#818cf8', '#4f46e5']

export default function ToolUsageChart({ toolCalls }: Props) {
  const data = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const tc of toolCalls) {
      counts[tc.tool_name] = (counts[tc.tool_name] || 0) + 1
    }
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15)
  }, [toolCalls])

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Tool Usage</h2>
        <p className="text-gray-600 text-sm">No tool calls found</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">MCP Tool Usage</h2>
      <ResponsiveContainer width="100%" height={Math.max(300, data.length * 36)}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <YAxis dataKey="name" type="category" width={160} tick={{ fill: '#d1d5db', fontSize: 12 }} />
          <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#f9fafb' }} />
          <Bar dataKey="count" name="Calls" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
