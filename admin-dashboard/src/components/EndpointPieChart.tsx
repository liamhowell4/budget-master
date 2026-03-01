import { useMemo } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import type { TokenUsageDoc } from '../types'

interface Props {
  tokenUsage: TokenUsageDoc[]
}

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export default function EndpointPieChart({ tokenUsage }: Props) {
  const data = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const doc of tokenUsage) {
      const ep = doc.endpoint || 'unknown'
      counts[ep] = (counts[ep] || 0) + 1
    }
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [tokenUsage])

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">By Endpoint</h2>
        <p className="text-gray-600 text-sm">No data</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">API Calls by Endpoint</h2>
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={80}
            outerRadius={130}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#f9fafb' }} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
