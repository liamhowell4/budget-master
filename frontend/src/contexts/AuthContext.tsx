import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  type ReactNode,
} from 'react'
import {
  onAuthChange,
  signInWithGoogle,
  signInWithGithub,
  signInWithEmail,
  signUpWithEmail,
  signOut as firebaseSignOut,
  getIdToken,
  type User,
} from '@/lib/firebase'
import { invalidateBudgetCache } from '@/hooks/useBudget'
import { invalidateExpensesCache } from '@/hooks/useExpenses'

// Clear all user-specific data caches
function clearAllUserCaches() {
  invalidateBudgetCache()
  invalidateExpensesCache()
}

interface AuthContextValue {
  user: User | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signInWithGithub: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  signUpWithEmail: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  getToken: () => Promise<string | null>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const previousUserIdRef = useRef<string | null>(null)

  useEffect(() => {
    const unsubscribe = onAuthChange((newUser) => {
      const newUserId = newUser?.uid ?? null
      const previousUserId = previousUserIdRef.current

      // Clear caches when user changes (different user or logout)
      if (previousUserId !== null && previousUserId !== newUserId) {
        clearAllUserCaches()
      }

      previousUserIdRef.current = newUserId
      setUser(newUser)
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  const handleSignInWithGoogle = async () => {
    await signInWithGoogle()
  }

  const handleSignInWithGithub = async () => {
    await signInWithGithub()
  }

  const handleSignInWithEmail = async (email: string, password: string) => {
    await signInWithEmail(email, password)
  }

  const handleSignUpWithEmail = async (email: string, password: string) => {
    await signUpWithEmail(email, password)
  }

  const handleSignOut = async () => {
    // Clear all cached user data before signing out
    clearAllUserCaches()
    await firebaseSignOut()
  }

  const getToken = async () => {
    return getIdToken()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signInWithGoogle: handleSignInWithGoogle,
        signInWithGithub: handleSignInWithGithub,
        signInWithEmail: handleSignInWithEmail,
        signUpWithEmail: handleSignUpWithEmail,
        signOut: handleSignOut,
        getToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
