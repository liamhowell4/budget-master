import type { ReactNode } from 'react'
import { Header } from './Header'

interface MainLayoutProps {
  children: ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <Header />
      <main className="flex-1">
        {children}
      </main>
    </div>
  )
}
