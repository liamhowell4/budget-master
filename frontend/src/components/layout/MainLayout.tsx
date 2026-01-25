import type { ReactNode } from 'react'
import { Header } from './Header'

interface MainLayoutProps {
  children: ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-[100dvh] bg-white dark:bg-neutral-950">
      <Header />
      <main className="flex-1">
        {children}
      </main>
    </div>
  )
}
