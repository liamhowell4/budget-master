import { useMemo, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'
import type { TokenUsageDoc, ToolCallDoc } from '../types'
import { FloatingTooltip, TOOLTIP_WRAPPER } from './ChartTooltip'

type Metric = 'tokens' | 'tools'

interface Props {
  tokenUsage: TokenUsageDoc[]
  toolCalls: ToolCallDoc[]
  uidToName: Record<string, string>
}

const COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#3b82f6', '#84cc16',
]

export default function StackedTokenChart({ tokenUsage, toolCalls, uidToName }: Props) {
  const [metric, setMetric] = useState<Metric>('tokens')

  // Get all unique UIDs sorted by total tokens descending
  const usersSorted = useMemo(() => {
    const totals: Record<string, number> = {}
    for (const doc of tokenUsage) {
      totals[doc.uid] = (totals[doc.uid] || 0) + (doc.input_tokens || 0) + (doc.output_tokens || 0)
    }
    // Also include users that only appear in toolCalls
    for (const doc of toolCalls) {
      if (!(doc.uid in totals)) totals[doc.uid] = 0
    }
    return Object.entries(totals)
      .sort((a, b) => b[1] - a[1])
      .map(([uid]) => uid)
  }, [tokenUsage, toolCalls])

  // All users enabled by default
  const [enabledUids, setEnabledUids] = useState<Set<string> | null>(null)

  // Lazy init: once usersSorted is ready, default to all enabled
  const enabled = enabledUids ?? new Set(usersSorted)

  const toggle = (uid: string) => {
    const next = new Set(enabled)
    if (next.has(uid)) {
      next.delete(uid)
    } else {
      next.add(uid)
    }
    setEnabledUids(next)
  }

  const enableAll = () => setEnabledUids(new Set(usersSorted))
  const disableAll = () => setEnabledUids(new Set())

  // Build stacked data based on metric
  const data = useMemo(() => {
    const enabledUidList = usersSorted.filter((uid) => enabled.has(uid))
    const byDay: Record<string, Record<string, number>> = {}

    if (metric === 'tokens') {
      for (const doc of tokenUsage) {
        if (!enabled.has(doc.uid)) continue
        const date = doc.timestamp ? doc.timestamp.slice(0, 10) : 'unknown'
        if (!byDay[date]) byDay[date] = {}
        byDay[date][doc.uid] = (byDay[date][doc.uid] || 0) + (doc.input_tokens || 0) + (doc.output_tokens || 0)
      }
    } else {
      for (const doc of toolCalls) {
        if (!enabled.has(doc.uid)) continue
        const date = doc.timestamp ? doc.timestamp.slice(0, 10) : 'unknown'
        if (!byDay[date]) byDay[date] = {}
        byDay[date][doc.uid] = (byDay[date][doc.uid] || 0) + 1
      }
    }

    return Object.entries(byDay)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, users]) => {
        const row: Record<string, string | number> = { date }
        for (const uid of enabledUidList) {
          row[uid] = users[uid] || 0
        }
        return row
      })
  }, [tokenUsage, toolCalls, enabled, usersSorted, metric])

  const colorMap = useMemo(() => {
    const map: Record<string, string> = {}
    usersSorted.forEach((uid, i) => {
      map[uid] = COLORS[i % COLORS.length]
    })
    return map
  }, [usersSorted])

  const getName = (uid: string) => uidToName[uid] || uid.slice(0, 8)

  const metricLabel = metric === 'tokens' ? 'Tokens' : 'Tool Calls'

  if (usersSorted.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">{metricLabel} by User (Stacked)</h2>
        <p className="text-gray-600 text-sm">No data</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 overflow-visible">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-gray-400">{metricLabel} by User (Stacked)</h2>
          <div className="flex rounded-md overflow-hidden border border-gray-700">
            <button
              onClick={() => setMetric('tokens')}
              className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                metric === 'tokens'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Tokens
            </button>
            <button
              onClick={() => setMetric('tools')}
              className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                metric === 'tools'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Tools
            </button>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={enableAll}
            className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
          >
            All
          </button>
          <button
            onClick={disableAll}
            className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
          >
            None
          </button>
        </div>
      </div>

      {/* User toggles */}
      <div className="flex flex-wrap gap-2 mb-4">
        {usersSorted.map((uid) => {
          const active = enabled.has(uid)
          return (
            <button
              key={uid}
              onClick={() => toggle(uid)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                active
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-800/40 text-gray-600 line-through'
              }`}
            >
              <span
                className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{
                  backgroundColor: active ? colorMap[uid] : '#374151',
                }}
              />
              {getName(uid)}
            </button>
          )
        })}
      </div>

      <ResponsiveContainer width="100%" height={320} style={{ overflow: 'visible' }}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 12 }}
            tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
          />
          <Tooltip
            wrapperStyle={TOOLTIP_WRAPPER}
            allowEscapeViewBox={{ x: true, y: true }}
            content={(props) => {
              const { active, payload, label, coordinate, viewBox } = props as any
              if (!active || !payload?.length) return null
              const unit = metric === 'tokens' ? ' tokens' : ' calls'
              const activeEntries = (payload as any[]).filter((p: any) => (p.value as number) > 0)
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
                  <div style={{ borderTop: '1px solid #374151', marginTop: 4, paddingTop: 4, color: '#9ca3af', fontSize: 11 }}>
                    {activeEntries.reduce((s: number, p: any) => s + (p.value as number), 0).toLocaleString()}{unit} total
                  </div>
                </FloatingTooltip>
              )
            }}
          />
          <Legend formatter={(value) => getName(value)} />
          {usersSorted.filter((uid) => enabled.has(uid)).map((uid) => (
            <Area
              key={uid}
              type="monotone"
              dataKey={uid}
              stackId="1"
              stroke={colorMap[uid]}
              fill={colorMap[uid]}
              fillOpacity={0.6}
              name={uid}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
