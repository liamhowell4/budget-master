import { cn } from '@/utils/cn'
import { MessageCircle, LayoutDashboard, Receipt } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

const tabs = [
  { id: 'chat', path: '/chat', icon: MessageCircle, label: 'Chat' },
  { id: 'dashboard', path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'expenses', path: '/expenses', icon: Receipt, label: 'Expenses' },
] as const

interface LiquidGlassTabBarProps {
  pendingCount?: number
}

/**
 * Apple Liquid Glass style floating tab bar
 * - Frosted glass effect with backdrop blur
 * - Floating pill shape centered at bottom
 * - Active tab gets gradient glow
 */
export function LiquidGlassTabBar({ pendingCount = 0 }: LiquidGlassTabBarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const currentPath = location.pathname

  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 safe-bottom">
      {/* Outer ambient glow */}
      <div className="absolute inset-0 rounded-full glow-gradient opacity-15 blur-2xl" />

      {/* Tab bar container */}
      <nav
        className={cn(
          'relative flex items-center gap-1 px-2 py-2',
          'rounded-full',
          // Frosted glass effect
          'bg-white/70 dark:bg-black/50',
          'backdrop-blur-2xl backdrop-saturate-150',
          // Border
          'border border-white/30 dark:border-white/10',
          // Shadow
          'shadow-lg shadow-black/10 dark:shadow-black/40'
        )}
      >
        {tabs.map((tab) => {
          const isActive = currentPath.startsWith(tab.path)
          const Icon = tab.icon
          const showBadge = tab.id === 'expenses' && pendingCount > 0

          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              className={cn(
                'relative flex items-center justify-center',
                'h-12 w-12 rounded-full',
                'transition-all duration-300',
                isActive
                  ? 'glow-gradient text-white glow-shadow-soft'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/50 dark:hover:bg-white/10'
              )}
              aria-label={tab.label}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className="h-5 w-5" strokeWidth={isActive ? 2 : 1.5} />

              {/* Badge for pending count */}
              {showBadge && (
                <span
                  className={cn(
                    'absolute -right-1 -top-1',
                    'flex h-5 w-5 items-center justify-center',
                    'rounded-full text-xs font-semibold',
                    'bg-red-500 text-white'
                  )}
                >
                  {pendingCount > 9 ? '9+' : pendingCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
