import { cn } from '@/utils/cn'
import { Sun, Moon, Check, Monitor } from 'lucide-react'
import { useTheme, COLOR_SCHEMES, type ColorScheme } from '@/contexts/ThemeContext'

export function AppearanceTab() {
  const {
    colorScheme,
    useSystemTheme,
    preferredLightTheme,
    preferredDarkTheme,
    setUseSystemTheme,
    setManualTheme,
    setPreferredTheme,
    getSchemesForMode,
  } = useTheme()

  const lightSchemes = getSchemesForMode('light')
  const darkSchemes = getSchemesForMode('dark')

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium text-[var(--text-primary)] mb-1">
          Appearance
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          Choose your preferred color theme
        </p>
      </div>

      {/* System Theme Toggle */}
      <div
        className={cn(
          'flex items-center justify-between p-4 rounded-lg border transition-colors',
          useSystemTheme
            ? 'bg-[var(--accent-muted)] border-[var(--accent-primary)]'
            : 'bg-[var(--surface-secondary)] border-[var(--border-primary)]'
        )}
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            useSystemTheme
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--surface-hover)] text-[var(--text-muted)]'
          )}>
            <Monitor className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Use system setting
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              Automatically switch between light and dark themes
            </p>
          </div>
        </div>
        <button
          onClick={() => setUseSystemTheme(!useSystemTheme)}
          className={cn(
            'relative w-11 h-6 rounded-full transition-colors',
            useSystemTheme
              ? 'bg-[var(--accent-primary)]'
              : 'bg-neutral-300 dark:bg-neutral-600'
          )}
        >
          <div
            className={cn(
              'absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform pointer-events-none',
              useSystemTheme ? 'translate-x-6' : 'translate-x-1'
            )}
          />
        </button>
      </div>

      {useSystemTheme ? (
        /* System Theme Mode - Show separate light/dark selectors */
        <>
          {/* Light Theme Preference */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sun className="h-4 w-4 text-[var(--text-muted)]" />
              <span className="text-sm font-medium text-[var(--text-secondary)]">
                Light Mode Theme
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {lightSchemes.map((scheme) => (
                <ThemeOption
                  key={scheme}
                  scheme={scheme}
                  isSelected={preferredLightTheme === scheme}
                  onClick={() => setPreferredTheme('light', scheme)}
                />
              ))}
            </div>
          </div>

          {/* Dark Theme Preference */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Moon className="h-4 w-4 text-[var(--text-muted)]" />
              <span className="text-sm font-medium text-[var(--text-secondary)]">
                Dark Mode Theme
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {darkSchemes.map((scheme) => (
                <ThemeOption
                  key={scheme}
                  scheme={scheme}
                  isSelected={preferredDarkTheme === scheme}
                  onClick={() => setPreferredTheme('dark', scheme)}
                />
              ))}
            </div>
          </div>
        </>
      ) : (
        /* Manual Theme Mode - Show all themes */
        <>
          {/* Light Themes */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sun className="h-4 w-4 text-[var(--text-muted)]" />
              <span className="text-sm font-medium text-[var(--text-secondary)]">
                Light Themes
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {lightSchemes.map((scheme) => (
                <ThemeOption
                  key={scheme}
                  scheme={scheme}
                  isSelected={colorScheme === scheme}
                  onClick={() => setManualTheme(scheme)}
                />
              ))}
            </div>
          </div>

          {/* Dark Themes */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Moon className="h-4 w-4 text-[var(--text-muted)]" />
              <span className="text-sm font-medium text-[var(--text-secondary)]">
                Dark Themes
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {darkSchemes.map((scheme) => (
                <ThemeOption
                  key={scheme}
                  scheme={scheme}
                  isSelected={colorScheme === scheme}
                  onClick={() => setManualTheme(scheme)}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

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
        'flex items-center gap-3 p-3 rounded-lg transition-colors border',
        isSelected
          ? 'bg-[var(--accent-muted)] border-[var(--accent-primary)]'
          : 'bg-[var(--surface-secondary)] border-[var(--border-primary)] hover:bg-[var(--surface-hover)]'
      )}
    >
      {/* Color preview swatch */}
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border"
        style={{
          backgroundColor: colors.bg,
          borderColor: info.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
        }}
      >
        <div
          className="w-4 h-4 rounded-full"
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
