import { useEffect, useState, useMemo } from 'react'
import { fetchUsers, fetchAnalytics } from './api'
import type { User, TokenUsageDoc, ToolCallDoc, AnalyticsSummary } from './types'
import OverviewCards from './components/OverviewCards'
import DailyActivityChart from './components/DailyActivityChart'
import UserTable from './components/UserTable'
import ToolUsageChart from './components/ToolUsageChart'
import EndpointPieChart from './components/EndpointPieChart'

type Tab = 'overview' | 'users' | 'tools' | 'endpoints'
type DayRange = 7 | 14 | 30 | 90

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [days, setDays] = useState<DayRange>(30)
  const [users, setUsers] = useState<User[]>([])
  const [tokenUsage, setTokenUsage] = useState<TokenUsageDoc[]>([])
  const [toolCalls, setToolCalls] = useState<ToolCallDoc[]>([])
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([fetchUsers(), fetchAnalytics(days)])
      .then(([usersData, analyticsData]) => {
        setUsers(usersData.users)
        setTokenUsage(analyticsData.token_usage)
        setToolCalls(analyticsData.tool_calls)
        setSummary(analyticsData.summary)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [days])

  const uidToName = useMemo(() => {
    const map: Record<string, string> = {}
    for (const u of users) {
      map[u.uid] = u.display_name || u.email || u.uid
    }
    return map
  }, [users])

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'users', label: 'By User' },
    { id: 'tools', label: 'By Tool' },
    { id: 'endpoints', label: 'By Endpoint' },
  ]

  const dayOptions: DayRange[] = [7, 14, 30, 90]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Budget Master Admin</h1>
        <div className="flex gap-2">
          {dayOptions.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                days === d
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-6">
        <div className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="px-6 py-6">
        {loading && (
          <div className="text-center text-gray-500 py-20">Loading...</div>
        )}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-400">
            Error: {error}
          </div>
        )}
        {!loading && !error && summary && (
          <>
            <OverviewCards summary={summary} toolCalls={toolCalls} />
            <div className="mt-6">
              <DailyActivityChart tokenUsage={tokenUsage} />
            </div>
            <div className="mt-6">
              {tab === 'overview' && null}
              {tab === 'users' && (
                <UserTable tokenUsage={tokenUsage} toolCalls={toolCalls} uidToName={uidToName} />
              )}
              {tab === 'tools' && <ToolUsageChart toolCalls={toolCalls} />}
              {tab === 'endpoints' && <EndpointPieChart tokenUsage={tokenUsage} />}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
