import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'
import type { TokenUsageDoc } from '../types'

interface Props {
  tokenUsage: TokenUsageDoc[]
}

interface DayData {
  date: string
  calls: number
  tokens: number
}

export default function DailyActivityChart({ tokenUsage }: Props) {
  const data = useMemo((): DayData[] => {
    const byDay: Record<string, DayData> = {}
    for (const doc of tokenUsage) {
      const date = doc.timestamp ? doc.timestamp.slice(0, 10) : 'unknown'
      if (!byDay[date]) byDay[date] = { date, calls: 0, tokens: 0 }
      byDay[date].calls += 1
      byDay[date].tokens += (doc.input_tokens || 0) + (doc.output_tokens || 0)
    }
    return Object.values(byDay).sort((a, b) => a.date.localeCompare(b.date))
  }, [tokenUsage])

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Daily Activity</h2>
        <p className="text-gray-600 text-sm">No data</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">Daily Activity</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <YAxis yAxisId="left" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <YAxis yAxisId="right" orientation="right" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#f9fafb' }} />
          <Legend />
          <Line yAxisId="left" type="monotone" dataKey="calls" stroke="#6366f1" strokeWidth={2} dot={false} name="API Calls" />
          <Line yAxisId="right" type="monotone" dataKey="tokens" stroke="#10b981" strokeWidth={2} dot={false} name="Tokens" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
