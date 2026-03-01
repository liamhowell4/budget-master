export interface User {
  uid: string
  email: string | null
  display_name: string | null
  photo_url: string | null
  last_sign_in: number | null
  created_at: number | null
}

export interface TokenUsageDoc {
  uid: string
  model: string
  input_tokens: number
  output_tokens: number
  endpoint: string
  timestamp: string // ISO string
}

export interface ToolCallDoc {
  uid: string
  tool_name: string
  conversation_id: string
  timestamp: string | null
}

export interface AnalyticsSummary {
  total_api_calls: number
  total_input_tokens: number
  total_output_tokens: number
  unique_users: number
  date_range_days: number
}

export interface AnalyticsResponse {
  token_usage: TokenUsageDoc[]
  tool_calls: ToolCallDoc[]
  summary: AnalyticsSummary
}

export interface UsersResponse {
  users: User[]
}
