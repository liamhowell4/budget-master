import { cn } from '@/utils/cn'
import { LogOut, ChevronDown, Settings } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { useLocation, useNavigate } from 'react-router-dom'
import { SegmentedControl } from '@/components/ui'

const navItems = [
  { value: '/expenses', label: 'Expenses' },
  { value: '/chat', label: 'Chat' },
  { value: '/dashboard', label: 'Dashboard' },
]

export function Header() {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { user, signOut } = useAuth()
  const { colorScheme } = useTheme()
  const isLiquidTheme = colorScheme.includes('liquid')
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header
      className={cn(
        'sticky top-0 z-40',
        'grid grid-cols-3 items-center',
        'h-14 px-4',
        'transition-colors duration-200',
        isLiquidTheme
          ? 'liquid-glass-nav'
          : 'bg-[var(--bg-primary)] border-b border-[var(--border-primary)]'
      )}
    >
      {/* Logo/Title - Left */}
      <div className="flex items-center gap-2">
        <img src="/favicon.svg" alt="" className="h-5 w-5" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">
          Budget Master
        </span>
      </div>

      {/* Centered Navigation */}
      <div className="hidden sm:flex justify-center">
        <SegmentedControl
          options={navItems}
          value={location.pathname}
          onChange={(path) => navigate(path)}
          size="sm"
        />
      </div>

      {/* Spacer for mobile */}
      <div className="hidden max-sm:block" />

      {/* Right side */}
      <div className="flex items-center justify-end gap-2">
        {/* User dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className={cn(
              'flex items-center gap-2 px-2 py-1.5 rounded-md transition-colors',
              'hover:bg-[var(--surface-hover)]'
            )}
          >
            {user?.photoURL ? (
              <img
                src={user.photoURL}
                alt=""
                className="h-6 w-6 rounded-full"
              />
            ) : (
              <div className="h-6 w-6 rounded-full bg-[var(--surface-secondary)] flex items-center justify-center">
                <span className="text-xs font-medium text-[var(--text-secondary)]">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
            )}
            <ChevronDown className="h-3 w-3 text-[var(--text-muted)]" />
          </button>

          {dropdownOpen && (
            <div
              className={cn(
                'absolute right-0 top-full mt-1 w-56',
                'rounded-lg',
                'bg-[var(--surface-primary)]',
                'border border-[var(--border-primary)]',
                'shadow-lg',
                'py-1'
              )}
            >
              {/* User info */}
              <div className="px-3 py-2 border-b border-[var(--border-primary)]">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {user?.displayName || 'User'}
                </p>
                <p className="text-xs text-[var(--text-muted)] truncate">
                  {user?.email}
                </p>
              </div>

              {/* Mobile nav */}
              <div className="sm:hidden border-b border-[var(--border-primary)] py-1">
                {navItems.map((item) => (
                  <button
                    key={item.value}
                    onClick={() => {
                      navigate(item.value)
                      setDropdownOpen(false)
                    }}
                    className={cn(
                      'w-full px-3 py-2 text-left text-sm transition-colors',
                      location.pathname === item.value
                        ? 'text-[var(--text-primary)] bg-[var(--surface-secondary)]'
                        : 'text-[var(--text-muted)] hover:bg-[var(--surface-hover)]'
                    )}
                  >
                    {item.label}
                  </button>
                ))}
                {/* Thin divider before Settings on mobile */}
                <div className="my-1 mx-3 border-t border-[var(--border-primary)] opacity-50" />
                <button
                  onClick={() => {
                    navigate('/settings')
                    setDropdownOpen(false)
                  }}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors',
                    location.pathname === '/settings'
                      ? 'text-[var(--text-primary)] bg-[var(--surface-secondary)]'
                      : 'text-[var(--text-muted)] hover:bg-[var(--surface-hover)]'
                  )}
                >
                  <Settings className="h-4 w-4" />
                  Settings
                </button>
              </div>

              {/* Settings - Desktop only (always visible) */}
              <div className="hidden sm:block border-b border-[var(--border-primary)] py-1">
                <button
                  onClick={() => {
                    navigate('/settings')
                    setDropdownOpen(false)
                  }}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors',
                    location.pathname === '/settings'
                      ? 'text-[var(--text-primary)] bg-[var(--surface-secondary)]'
                      : 'text-[var(--text-muted)] hover:bg-[var(--surface-hover)]'
                  )}
                >
                  <Settings className="h-4 w-4" />
                  Settings
                </button>
              </div>

              {/* Sign out */}
              <button
                onClick={async () => {
                  await signOut()
                  setDropdownOpen(false)
                }}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2',
                  'text-sm text-[var(--text-muted)]',
                  'hover:bg-[var(--surface-hover)]',
                  'transition-colors'
                )}
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
