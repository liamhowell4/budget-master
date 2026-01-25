import { cn } from '@/utils/cn'
import { Moon, Sun, LogOut, ChevronDown } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { useLocation, useNavigate } from 'react-router-dom'
import { SegmentedControl } from '@/components/ui'

const navItems = [
  { value: '/chat', label: 'Chat' },
  { value: '/dashboard', label: 'Dashboard' },
  { value: '/expenses', label: 'Expenses' },
]

export function Header() {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { user, signOut } = useAuth()
  const { theme, toggleTheme } = useTheme()
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
        'bg-white dark:bg-neutral-950',
        'border-b border-neutral-200 dark:border-neutral-800'
      )}
    >
      {/* Logo/Title - Left */}
      <div className="flex items-center">
        <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          Finance
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
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={cn(
            'p-2 rounded-md transition-colors',
            'text-neutral-500 dark:text-neutral-400',
            'hover:bg-neutral-100 dark:hover:bg-neutral-800'
          )}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
        </button>

        {/* User dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className={cn(
              'flex items-center gap-2 px-2 py-1.5 rounded-md transition-colors',
              'hover:bg-neutral-100 dark:hover:bg-neutral-800'
            )}
          >
            {user?.photoURL ? (
              <img
                src={user.photoURL}
                alt=""
                className="h-6 w-6 rounded-full"
              />
            ) : (
              <div className="h-6 w-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
                <span className="text-xs font-medium text-neutral-600 dark:text-neutral-300">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
            )}
            <ChevronDown className="h-3 w-3 text-neutral-400" />
          </button>

          {dropdownOpen && (
            <div
              className={cn(
                'absolute right-0 top-full mt-1 w-56',
                'rounded-lg',
                'bg-white dark:bg-neutral-900',
                'border border-neutral-200 dark:border-neutral-800',
                'shadow-lg',
                'py-1'
              )}
            >
              {/* User info */}
              <div className="px-3 py-2 border-b border-neutral-200 dark:border-neutral-800">
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                  {user?.displayName || 'User'}
                </p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
                  {user?.email}
                </p>
              </div>

              {/* Mobile nav */}
              <div className="sm:hidden border-b border-neutral-200 dark:border-neutral-800 py-1">
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
                        ? 'text-neutral-900 dark:text-neutral-100 bg-neutral-50 dark:bg-neutral-800'
                        : 'text-neutral-500 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800'
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {/* Sign out */}
              <button
                onClick={async () => {
                  await signOut()
                  setDropdownOpen(false)
                }}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2',
                  'text-sm text-neutral-500 dark:text-neutral-400',
                  'hover:bg-neutral-50 dark:hover:bg-neutral-800',
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
