import { cn } from '@/utils/cn'
import { Moon, Sun, LogOut, ChevronDown, Palette, Check } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme, COLOR_SCHEMES, type ColorScheme } from '@/contexts/ThemeContext'
import { useLocation, useNavigate } from 'react-router-dom'
import { SegmentedControl } from '@/components/ui'

const navItems = [
  { value: '/chat', label: 'Chat' },
  { value: '/dashboard', label: 'Dashboard' },
  { value: '/expenses', label: 'Expenses' },
  { value: '/settings', label: 'Settings' },
]

export function Header() {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [themeDropdownOpen, setThemeDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const themeDropdownRef = useRef<HTMLDivElement>(null)
  const { user, signOut } = useAuth()
  const { colorScheme, setColorScheme, getSchemesForMode } = useTheme()
  const isLiquidTheme = colorScheme.includes('liquid')
  const location = useLocation()
  const navigate = useNavigate()

  const lightSchemes = getSchemesForMode('light')
  const darkSchemes = getSchemesForMode('dark')

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
      if (themeDropdownRef.current && !themeDropdownRef.current.contains(event.target as Node)) {
        setThemeDropdownOpen(false)
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
        {/* Theme dropdown */}
        <div className="relative" ref={themeDropdownRef}>
          <button
            onClick={() => setThemeDropdownOpen(!themeDropdownOpen)}
            className={cn(
              'flex items-center gap-1.5 px-2 py-1.5 rounded-md transition-colors',
              'text-[var(--text-secondary)]',
              'hover:bg-[var(--surface-hover)]'
            )}
            aria-label="Change theme"
          >
            <Palette className="h-4 w-4" />
            <span className="text-xs font-medium hidden sm:inline">
              {COLOR_SCHEMES[colorScheme].label}
            </span>
            <ChevronDown className="h-3 w-3" />
          </button>

          {themeDropdownOpen && (
            <div
              className={cn(
                'absolute right-0 top-full mt-1 w-72',
                'rounded-lg',
                'bg-[var(--surface-primary)]',
                'border border-[var(--border-primary)]',
                'shadow-lg',
                'p-2',
                'max-h-[80vh] overflow-y-auto'
              )}
            >
              {/* Light Themes */}
              <div className="mb-3">
                <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                  <Sun className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                  <span className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">
                    Light
                  </span>
                </div>
                <div className="space-y-0.5">
                  {lightSchemes.map((scheme) => (
                    <ThemeOption
                      key={scheme}
                      scheme={scheme}
                      isSelected={colorScheme === scheme}
                      onClick={() => {
                        setColorScheme(scheme)
                        setThemeDropdownOpen(false)
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Dark Themes */}
              <div>
                <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                  <Moon className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                  <span className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">
                    Dark
                  </span>
                </div>
                <div className="space-y-0.5">
                  {darkSchemes.map((scheme) => (
                    <ThemeOption
                      key={scheme}
                      scheme={scheme}
                      isSelected={colorScheme === scheme}
                      onClick={() => {
                        setColorScheme(scheme)
                        setThemeDropdownOpen(false)
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

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

// Theme option component with preview colors
function ThemeOption({
  scheme,
  isSelected,
  onClick,
}: {
  scheme: ColorScheme
  isSelected: boolean
  onClick: () => void
}) {
  const info = COLOR_SCHEMES[scheme]

  // Preview colors for each theme
  const previewColors: Record<ColorScheme, { bg: string; accent: string; text: string }> = {
    'light-original': { bg: '#ffffff', accent: '#3b82f6', text: '#171717' },
    'light-apple': { bg: '#ffffff', accent: '#007aff', text: '#000000' },
    'light-vibrant': { bg: '#ffffff', accent: '#2563eb', text: '#1a1a1a' },
    'light-glass': { bg: '#f8fafc', accent: '#6366f1', text: '#0f172a' },
    'light-soft': { bg: '#fefdfb', accent: '#8b9a83', text: '#3d3a36' },
    'light-liquid': { bg: '#f2f2f7', accent: '#007aff', text: '#1c1c1e' },
    'dark-original': { bg: '#000000', accent: '#818cf8', text: '#fafafa' },
    'dark-midnight': { bg: '#000000', accent: '#8b5cf6', text: '#f0f0ff' },
    'dark-sunset': { bg: '#000000', accent: '#f97316', text: '#fff8f0' },
    'dark-glass': { bg: '#000000', accent: '#a78bfa', text: '#ffffff' },
    'dark-liquid': { bg: '#000000', accent: '#0a84ff', text: '#ffffff' },
  }

  const colors = previewColors[scheme]

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 px-2 py-2 rounded-md transition-colors',
        isSelected
          ? 'bg-[var(--accent-muted)]'
          : 'hover:bg-[var(--surface-hover)]'
      )}
    >
      {/* Color preview swatch */}
      <div
        className="w-8 h-8 rounded-md flex items-center justify-center shrink-0 border"
        style={{
          backgroundColor: colors.bg,
          borderColor: info.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
        }}
      >
        <div
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: colors.accent }}
        />
      </div>

      {/* Label and description */}
      <div className="flex-1 text-left min-w-0">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          {info.label}
        </p>
        <p className="text-xs text-[var(--text-muted)] truncate">
          {info.description}
        </p>
      </div>

      {/* Checkmark */}
      {isSelected && (
        <Check className="h-4 w-4 text-[var(--accent-primary)] shrink-0" />
      )}
    </button>
  )
}
