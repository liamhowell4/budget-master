import type { AnalyticsSummary, ToolCallDoc } from '../types'

interface Props {
  summary: AnalyticsSummary
  toolCalls: ToolCallDoc[]
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white truncate">{value}</p>
    </div>
  )
}

export default function OverviewCards({ summary, toolCalls }: Props) {
  // Find top tool by count
  const toolCounts: Record<string, number> = {}
  for (const tc of toolCalls) {
    toolCounts[tc.tool_name] = (toolCounts[tc.tool_name] || 0) + 1
  }
  const topTool = Object.entries(toolCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—'

  const totalTokens = (summary.total_input_tokens + summary.total_output_tokens).toLocaleString()

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card label="API Calls" value={summary.total_api_calls.toLocaleString()} />
      <Card label="Total Tokens" value={totalTokens} />
      <Card label="Unique Users" value={summary.unique_users.toString()} />
      <Card label="Top Tool" value={topTool} />
    </div>
  )
}
