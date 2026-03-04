import { useEffect, useState, useMemo, useCallback } from 'react'
import { fetchUsers, fetchAnalytics } from './api'
import type { User, TokenUsageDoc, ToolCallDoc, AnalyticsSummary } from './types'
import OverviewCards from './components/OverviewCards'
import DailyActivityChart from './components/DailyActivityChart'
import UserTable from './components/UserTable'
import ToolUsageChart from './components/ToolUsageChart'
import EndpointPieChart from './components/EndpointPieChart'
import StackedTokenChart from './components/StackedTokenChart'
import ToolUserBreakdown from './components/ToolUserBreakdown'
import ChatPill from './components/ChatPill'

type Tab = 'overview' | 'users' | 'tools' | 'endpoints'
type DayRange = 7 | 14 | 30 | 90

const VALID_TABS: Tab[] = ['overview', 'users', 'tools', 'endpoints']
const VALID_DAYS: DayRange[] = [7, 14, 30, 90]

function parseHash(): { tab: Tab; days: DayRange } {
  const hash = window.location.hash.replace('#/', '').replace('#', '')
  const [tabPart, queryPart] = hash.split('?')
  const tab = VALID_TABS.includes(tabPart as Tab) ? (tabPart as Tab) : 'overview'
  let days: DayRange = 7
  if (queryPart) {
    const params = new URLSearchParams(queryPart)
    const d = Number(params.get('days'))
    if (VALID_DAYS.includes(d as DayRange)) days = d as DayRange
  }
  return { tab, days }
}

function setHash(tab: Tab, days: DayRange) {
  const daysParam = days !== 7 ? `?days=${days}` : ''
  window.location.hash = `#/${tab}${daysParam}`
}

export default function App() {
  const initial = parseHash()
  const [tab, setTabState] = useState<Tab>(initial.tab)
  const [days, setDaysState] = useState<DayRange>(initial.days)
  const [users, setUsers] = useState<User[]>([])
  const [tokenUsage, setTokenUsage] = useState<TokenUsageDoc[]>([])
  const [toolCalls, setToolCalls] = useState<ToolCallDoc[]>([])
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedUid, setSelectedUid] = useState<string | undefined>(undefined)

  const setTab = useCallback((t: Tab) => {
    setTabState(t)
    setSelectedUid(undefined)
    setHash(t, days)
  }, [days])

  const setDays = useCallback((d: DayRange) => {
    setDaysState(d)
    setHash(tab, d)
  }, [tab])

  // Sync from hash on popstate (back/forward)
  useEffect(() => {
    const onHashChange = () => {
      const parsed = parseHash()
      setTabState(parsed.tab)
      setDaysState(parsed.days)
      setSelectedUid(undefined)
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

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

  const dayOptions: DayRange[] = VALID_DAYS

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
      <main className="px-6 py-6 pb-24">
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
                <>
                  <UserTable
                    tokenUsage={tokenUsage}
                    toolCalls={toolCalls}
                    uidToName={uidToName}
                    selectedUid={selectedUid}
                    onSelectUid={setSelectedUid}
                  />
                  <div className="mt-6">
                    <StackedTokenChart
                      tokenUsage={tokenUsage}
                      toolCalls={toolCalls}
                      uidToName={uidToName}
                    />
                  </div>
                  <div className="mt-6">
                    <DailyActivityChart
                      tokenUsage={tokenUsage}
                      filterUid={selectedUid}
                      title={
                        selectedUid
                          ? `Daily Activity — ${uidToName[selectedUid] ?? selectedUid}`
                          : 'Daily Activity — All Users'
                      }
                    />
                  </div>
                </>
              )}
              {tab === 'tools' && (
                <>
                  <ToolUsageChart toolCalls={toolCalls} />
                  <div className="mt-6">
                    <ToolUserBreakdown toolCalls={toolCalls} uidToName={uidToName} />
                  </div>
                </>
              )}
              {tab === 'endpoints' && <EndpointPieChart tokenUsage={tokenUsage} />}
            </div>
          </>
        )}
      </main>
      <ChatPill summary={summary} tokenUsage={tokenUsage} toolCalls={toolCalls} />
    </div>
  )
}
