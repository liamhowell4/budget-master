import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL as string
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY as string

const client = axios.create({
  baseURL: API_URL,
  headers: { 'X-API-Key': ADMIN_API_KEY },
})

export async function fetchUsers() {
  const res = await client.get('/admin/users')
  return res.data
}

export async function fetchAnalytics(days: number) {
  const res = await client.get(`/admin/analytics?days=${days}`)
  return res.data
}
