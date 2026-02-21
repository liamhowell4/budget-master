import { initializeApp, type FirebaseApp } from 'firebase/app'
import {
  getAuth,
  GoogleAuthProvider,
  GithubAuthProvider,
  OAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  updateProfile as firebaseUpdateProfile,
  updatePassword as firebaseUpdatePassword,
  EmailAuthProvider,
  reauthenticateWithCredential,
  type User,
  type Auth,
} from 'firebase/auth'

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

// Initialize Firebase
let app: FirebaseApp
let auth: Auth

try {
  app = initializeApp(firebaseConfig)
  auth = getAuth(app)
} catch (error) {
  console.error('Firebase initialization error:', error)
  throw error
}

// Auth providers
const googleProvider = new GoogleAuthProvider()
const githubProvider = new GithubAuthProvider()
const appleProvider = new OAuthProvider('apple.com')

// Auth methods
export async function signInWithGoogle(): Promise<User> {
  const result = await signInWithPopup(auth, googleProvider)
  return result.user
}

export async function signInWithGithub(): Promise<User> {
  const result = await signInWithPopup(auth, githubProvider)
  return result.user
}

export async function signInWithApple(): Promise<User> {
  const result = await signInWithPopup(auth, appleProvider)
  return result.user
}

export async function signInWithEmail(email: string, password: string): Promise<User> {
  const result = await signInWithEmailAndPassword(auth, email, password)
  return result.user
}

export async function signUpWithEmail(email: string, password: string): Promise<User> {
  const result = await createUserWithEmailAndPassword(auth, email, password)
  return result.user
}

export async function signOut(): Promise<void> {
  await firebaseSignOut(auth)
}

export async function getIdToken(): Promise<string | null> {
  const user = auth.currentUser
  if (!user) return null
  return user.getIdToken()
}

export function onAuthChange(callback: (user: User | null) => void): () => void {
  return onAuthStateChanged(auth, callback)
}

export async function updateDisplayName(displayName: string): Promise<void> {
  const user = auth.currentUser
  if (!user) throw new Error('No user logged in')
  await firebaseUpdateProfile(user, { displayName })
}

export async function updatePassword(currentPassword: string, newPassword: string): Promise<void> {
  const user = auth.currentUser
  if (!user || !user.email) throw new Error('No user logged in')

  // Re-authenticate with current password first
  const credential = EmailAuthProvider.credential(user.email, currentPassword)
  await reauthenticateWithCredential(user, credential)

  // Then update password
  await firebaseUpdatePassword(user, newPassword)
}

export function getAuthProvider(user: User | null): 'email' | 'google' | 'github' | 'apple' | null {
  if (!user) return null
  const providerData = user.providerData
  if (!providerData.length) return null

  const providerId = providerData[0].providerId
  if (providerId === 'password') return 'email'
  if (providerId === 'google.com') return 'google'
  if (providerId === 'github.com') return 'github'
  if (providerId === 'apple.com') return 'apple'
  return null
}

export { auth, app }
export type { User }
