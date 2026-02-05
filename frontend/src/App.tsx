import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Spinner, LiquidGlassFilter } from '@/components/ui'
import { Header } from '@/components/layout'
import { LoginPage, ChatPage, DashboardPage, ExpensesPage, SettingsPage } from '@/pages'

function ProtectedLayout() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-primary)]">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-primary)]">
        <Spinner size="lg" />
      </div>
    )
  }

  if (user) {
    return <Navigate to="/chat" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      {/* SVG filters for liquid glass refraction effect */}
      <LiquidGlassFilter />

      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />

        {/* Protected routes with persistent layout */}
        <Route element={<ProtectedLayout />}>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/expenses" element={<ExpensesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
