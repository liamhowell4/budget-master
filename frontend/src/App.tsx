import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Spinner, LiquidGlassFilter } from '@/components/ui'
import { Header } from '@/components/layout'
import { LoginPage, ChatPage, DashboardPage, ExpensesPage, SettingsPage } from '@/pages'
import { OnboardingWizard } from '@/components/onboarding'
import { useOnboardingCheck } from '@/hooks/useOnboardingCheck'

function ProtectedLayout() {
  const { user, loading: authLoading } = useAuth()
  const { needsOnboarding, loading: onboardingLoading, recheckOnboarding } = useOnboardingCheck()
  const [showWizard, setShowWizard] = useState(false)

  // Show wizard when onboarding is needed
  useEffect(() => {
    if (needsOnboarding === true) {
      setShowWizard(true)
    }
  }, [needsOnboarding])

  // Loading state
  if (authLoading || onboardingLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-primary)]">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  const handleOnboardingComplete = () => {
    setShowWizard(false)
    recheckOnboarding()
    // Dispatch event to notify hooks to refetch data
    window.dispatchEvent(new CustomEvent('onboarding-complete'))
  }

  const handleOnboardingSkip = () => {
    setShowWizard(false)
  }

  return (
    <>
      {showWizard && (
        <OnboardingWizard
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
        />
      )}
      <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
        <Header />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </>
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
