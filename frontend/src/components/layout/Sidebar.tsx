import { cn } from '@/utils/cn'
import { MessageSquare, LayoutDashboard, Receipt, X } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

const navItems = [
  { path: '/expenses', label: 'Expenses', icon: Receipt },
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()

  const handleNavigation = (path: string) => {
    navigate(path)
    onClose()
  }

  return (
    <>
      {/* Backdrop for mobile overlay */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 transition-opacity lg:hidden',
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-14 bottom-0 left-0 z-40 w-64',
          'bg-white dark:bg-neutral-950',
          'border-r border-neutral-200 dark:border-neutral-800',
          'flex flex-col',
          'transition-transform duration-200 ease-in-out',
          // Desktop: always visible
          'lg:translate-x-0',
          // Mobile: slide in/out
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-end p-2 lg:hidden">
          <button
            onClick={onClose}
            className={cn(
              'p-2 rounded-md transition-colors',
              'text-neutral-500 dark:text-neutral-400',
              'hover:bg-neutral-100 dark:hover:bg-neutral-800'
            )}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                key={item.path}
                onClick={() => handleNavigation(item.path)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg',
                  'text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
                    : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/50'
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </button>
            )
          })}
        </nav>
      </aside>
    </>
  )
}
