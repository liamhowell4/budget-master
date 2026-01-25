import { cn } from '@/utils/cn'
import type { ReactNode } from 'react'

interface AuthLayoutProps {
  children: ReactNode
}

/**
 * Layout for auth pages (login/signup)
 * Centered content with dark theme support
 */
export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div
      className={cn(
        'min-h-[100dvh] w-full',
        'flex items-center justify-center',
        'bg-white dark:bg-neutral-950',
        'p-4'
      )}
    >
      {children}
    </div>
  )
}
