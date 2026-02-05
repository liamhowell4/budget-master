import { doc, getDoc, setDoc } from 'firebase/firestore'
import { getFirestore } from 'firebase/firestore'
import { app } from '@/lib/firebase'

const db = getFirestore(app)

export interface ThemePreferences {
  useSystemTheme: boolean
  preferredLightTheme: string
  preferredDarkTheme: string
  // When not using system theme, this is the manually selected theme
  manualTheme: string
}

export interface UserPreferences {
  theme: ThemePreferences
}

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: {
    useSystemTheme: false,
    preferredLightTheme: 'light-original',
    preferredDarkTheme: 'dark-original',
    manualTheme: 'light-original',
  },
}

export async function getUserPreferences(userId: string): Promise<UserPreferences> {
  try {
    const docRef = doc(db, 'user_preferences', userId)
    const docSnap = await getDoc(docRef)

    if (docSnap.exists()) {
      const data = docSnap.data()
      // Merge with defaults to handle missing fields
      return {
        ...DEFAULT_PREFERENCES,
        ...data,
        theme: {
          ...DEFAULT_PREFERENCES.theme,
          ...data.theme,
        },
      }
    }

    return DEFAULT_PREFERENCES
  } catch (error) {
    console.error('Error fetching user preferences:', error)
    return DEFAULT_PREFERENCES
  }
}

export async function saveThemePreferences(
  userId: string,
  themePrefs: Partial<ThemePreferences>
): Promise<void> {
  try {
    const docRef = doc(db, 'user_preferences', userId)
    const docSnap = await getDoc(docRef)

    const currentPrefs = docSnap.exists() ? docSnap.data() : DEFAULT_PREFERENCES

    await setDoc(docRef, {
      ...currentPrefs,
      theme: {
        ...DEFAULT_PREFERENCES.theme,
        ...currentPrefs.theme,
        ...themePrefs,
      },
    }, { merge: true })
  } catch (error) {
    console.error('Error saving theme preferences:', error)
    throw error
  }
}
