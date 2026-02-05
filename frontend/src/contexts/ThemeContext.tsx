import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getUserPreferences, saveThemePreferences, type ThemePreferences } from '@/services/userPreferencesService'

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
  // Current active color scheme (resolved based on system or manual)
  colorScheme: ColorScheme
  // Whether using system theme
  useSystemTheme: boolean
  // Preferred themes for each mode (when using system theme)
  preferredLightTheme: ColorScheme
  preferredDarkTheme: ColorScheme
  // Loading state
  loading: boolean
  // Set whether to use system theme
  setUseSystemTheme: (use: boolean) => void
  // Set the manual theme (when not using system)
  setManualTheme: (scheme: ColorScheme) => void
  // Set preferred theme for a mode (when using system)
  setPreferredTheme: (mode: ThemeMode, scheme: ColorScheme) => void
  // Get all schemes for a given mode
  getSchemesForMode: (mode: ThemeMode) => ColorScheme[]
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const STORAGE_KEY = 'finance-bot-theme-prefs'

function getSystemMode(): ThemeMode {
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

function getModeFromScheme(scheme: ColorScheme): ThemeMode {
  return COLOR_SCHEMES[scheme].mode as ThemeMode
}

// Local storage fallback for when user is not logged in
function getLocalPrefs(): ThemePreferences {
  if (typeof window === 'undefined') {
    return {
      useSystemTheme: false,
      preferredLightTheme: 'light-original',
      preferredDarkTheme: 'dark-original',
      manualTheme: 'light-original',
    }
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch {
    // Ignore parse errors
  }

  // Check for legacy single theme storage
  const legacyTheme = localStorage.getItem('finance-bot-color-scheme') as ColorScheme | null
  if (legacyTheme && legacyTheme in COLOR_SCHEMES) {
    return {
      useSystemTheme: false,
      preferredLightTheme: 'light-original',
      preferredDarkTheme: 'dark-original',
      manualTheme: legacyTheme,
    }
  }

  const systemMode = getSystemMode()
  return {
    useSystemTheme: false,
    preferredLightTheme: 'light-original',
    preferredDarkTheme: 'dark-original',
    manualTheme: systemMode === 'dark' ? 'dark-original' : 'light-original',
  }
}

function saveLocalPrefs(prefs: ThemePreferences): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  }
}

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [systemMode, setSystemMode] = useState<ThemeMode>(getSystemMode)

  const [prefs, setPrefs] = useState<ThemePreferences>(getLocalPrefs)

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = (e: MediaQueryListEvent) => {
      setSystemMode(e.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  // Load preferences from Firebase when user logs in
  useEffect(() => {
    async function loadPreferences() {
      if (user) {
        setLoading(true)
        try {
          const userPrefs = await getUserPreferences(user.uid)
          const themePrefs = userPrefs.theme
          // Validate that stored themes still exist
          const validatedPrefs: ThemePreferences = {
            useSystemTheme: themePrefs.useSystemTheme,
            preferredLightTheme: (themePrefs.preferredLightTheme in COLOR_SCHEMES)
              ? themePrefs.preferredLightTheme as ColorScheme
              : 'light-original',
            preferredDarkTheme: (themePrefs.preferredDarkTheme in COLOR_SCHEMES)
              ? themePrefs.preferredDarkTheme as ColorScheme
              : 'dark-original',
            manualTheme: (themePrefs.manualTheme in COLOR_SCHEMES)
              ? themePrefs.manualTheme as ColorScheme
              : 'light-original',
          }
          setPrefs(validatedPrefs)
          saveLocalPrefs(validatedPrefs)
        } catch (error) {
          console.error('Failed to load theme preferences:', error)
        } finally {
          setLoading(false)
        }
      } else {
        // Not logged in, use local storage
        setPrefs(getLocalPrefs())
        setLoading(false)
      }
    }

    loadPreferences()
  }, [user])

  // Compute active color scheme
  const colorScheme: ColorScheme = prefs.useSystemTheme
    ? (systemMode === 'dark' ? prefs.preferredDarkTheme as ColorScheme : prefs.preferredLightTheme as ColorScheme)
    : prefs.manualTheme as ColorScheme

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

    // Add dark class for Tailwind dark: variants
    if (mode === 'dark') {
      root.classList.add('dark')
    }
  }, [colorScheme, mode])

  // Save preferences helper
  const savePrefs = useCallback(async (newPrefs: ThemePreferences) => {
    setPrefs(newPrefs)
    saveLocalPrefs(newPrefs)

    if (user) {
      try {
        await saveThemePreferences(user.uid, newPrefs)
      } catch (error) {
        console.error('Failed to save theme preferences:', error)
      }
    }
  }, [user])

  const setUseSystemTheme = useCallback((use: boolean) => {
    savePrefs({ ...prefs, useSystemTheme: use })
  }, [prefs, savePrefs])

  const setManualTheme = useCallback((scheme: ColorScheme) => {
    savePrefs({ ...prefs, manualTheme: scheme })
  }, [prefs, savePrefs])

  const setPreferredTheme = useCallback((targetMode: ThemeMode, scheme: ColorScheme) => {
    if (targetMode === 'light') {
      savePrefs({ ...prefs, preferredLightTheme: scheme })
    } else {
      savePrefs({ ...prefs, preferredDarkTheme: scheme })
    }
  }, [prefs, savePrefs])

  const getSchemesForMode = (targetMode: ThemeMode): ColorScheme[] => {
    return (Object.keys(COLOR_SCHEMES) as ColorScheme[]).filter(
      (scheme) => COLOR_SCHEMES[scheme].mode === targetMode
    )
  }

  return (
    <ThemeContext.Provider value={{
      mode,
      colorScheme,
      useSystemTheme: prefs.useSystemTheme,
      preferredLightTheme: prefs.preferredLightTheme as ColorScheme,
      preferredDarkTheme: prefs.preferredDarkTheme as ColorScheme,
      loading,
      setUseSystemTheme,
      setManualTheme,
      setPreferredTheme,
      getSchemesForMode,
    }}>
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
