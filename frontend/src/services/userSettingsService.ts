import api from './api'

export type SupportedModel =
  | 'claude-sonnet-4-6'
  | 'claude-haiku-4-5'
  | 'gpt-5-mini'
  | 'gpt-5.1'
  | 'gemini-3.1-pro'
  | 'gemini-3-flash'

export interface UserSettings {
  selected_model: SupportedModel
}

export async function getUserSettings(): Promise<UserSettings> {
  const response = await api.get<UserSettings>('/user/settings')
  return response.data
}

export async function updateUserSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  const response = await api.put<UserSettings>('/user/settings', settings)
  return response.data
}
