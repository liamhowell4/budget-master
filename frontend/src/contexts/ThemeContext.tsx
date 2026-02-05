import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

// All available color schemes
export const COLOR_SCHEMES = {
  // Light themes
  'light-original': { label: 'Original', mode: 'light', description: 'Clean neutral grays' },
  'light-apple': { label: 'Apple', mode: 'light', description: 'iOS-inspired, subtle blue' },
  'light-vibrant': { label: 'Vibrant', mode: 'light', description: 'Bold RGB primaries' },
  'light-glass': { label: 'Glass', mode: 'light', description: 'Frosted blur effects' },
  'light-soft': { label: 'Soft', mode: 'light', description: 'Muted pastels, calming' },
  'light-liquid': { label: 'Liquid Glass', mode: 'light', description: 'iOS 26 style, specular shine' },
  // Dark themes
  'dark-original': { label: 'Original', mode: 'dark', description: 'Neutral + purple/orange glow' },
  'dark-midnight': { label: 'Midnight', mode: 'dark', description: 'Deep purple accents' },
  'dark-sunset': { label: 'Sunset', mode: 'dark', description: 'Warm orange/coral' },
  'dark-glass': { label: 'Glass', mode: 'dark', description: 'Frosted blur effects' },
  'dark-liquid': { label: 'Liquid Glass', mode: 'dark', description: 'iOS 26 style, specular shine' },
} as const

export type ColorScheme = keyof typeof COLOR_SCHEMES
export type ThemeMode = 'light' | 'dark'

interface ThemeContextValue {
  // Current resolved theme (light or dark)
  mode: ThemeMode
  // Current color scheme
  colorScheme: ColorScheme
  // Set the color scheme directly
  setColorScheme: (scheme: ColorScheme) => void
  // Get all schemes for a given mode
  getSchemesForMode: (mode: ThemeMode) => ColorScheme[]
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const STORAGE_KEY = 'finance-bot-color-scheme'

function getSystemMode(): ThemeMode {
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

function getModeFromScheme(scheme: ColorScheme): ThemeMode {
  return COLOR_SCHEMES[scheme].mode as ThemeMode
}

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [colorScheme, setColorSchemeState] = useState<ColorScheme>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY) as ColorScheme | null
      if (stored && stored in COLOR_SCHEMES) {
        return stored
      }
      // Default based on system preference
      return getSystemMode() === 'dark' ? 'dark-original' : 'light-original'
    }
    return 'light-original'
  })

  const mode = getModeFromScheme(colorScheme)

  // Apply theme classes to document
  useEffect(() => {
    const root = document.documentElement

    // Remove all theme classes
    root.classList.remove('dark')
    Object.keys(COLOR_SCHEMES).forEach((scheme) => {
      root.classList.remove(`theme-${scheme}`)
    })

    // Add current theme class
    root.classList.add(`theme-${colorScheme}`)

    // Add dark class for Tailwind dark: variants (for any remaining hardcoded dark: styles)
    if (mode === 'dark') {
      root.classList.add('dark')
    }

    // Store preference
    localStorage.setItem(STORAGE_KEY, colorScheme)
  }, [colorScheme, mode])

  const setColorScheme = (scheme: ColorScheme) => {
    setColorSchemeState(scheme)
  }

  const getSchemesForMode = (targetMode: ThemeMode): ColorScheme[] => {
    return (Object.keys(COLOR_SCHEMES) as ColorScheme[]).filter(
      (scheme) => COLOR_SCHEMES[scheme].mode === targetMode
    )
  }

  return (
    <ThemeContext.Provider value={{ mode, colorScheme, setColorScheme, getSchemesForMode }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
