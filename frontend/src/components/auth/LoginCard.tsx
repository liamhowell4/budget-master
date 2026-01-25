import { cn } from '@/utils/cn'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Spinner } from '@/components/ui'
import { Github, ArrowRight } from 'lucide-react'

export function LoginCard() {
  const { signInWithGoogle, signInWithGithub, signInWithEmail, signUpWithEmail } =
    useAuth()

  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGoogleSignIn = async () => {
    setLoading('google')
    setError(null)
    try {
      await signInWithGoogle()
    } catch (err) {
      setError('Failed to sign in with Google')
      console.error(err)
    } finally {
      setLoading(null)
    }
  }

  const handleGithubSignIn = async () => {
    setLoading('github')
    setError(null)
    try {
      await signInWithGithub()
    } catch (err) {
      setError('Failed to sign in with GitHub')
      console.error(err)
    } finally {
      setLoading(null)
    }
  }

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading('email')
    setError(null)

    try {
      if (isSignUp) {
        await signUpWithEmail(email, password)
      } else {
        await signInWithEmail(email, password)
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Authentication failed'
      setError(message)
      console.error(err)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="w-full max-w-sm">
      {/* Card */}
      <div
        className={cn(
          'rounded-lg',
          'bg-white dark:bg-neutral-900',
          'border border-neutral-200 dark:border-neutral-800',
          'shadow-lg',
          'px-8 py-10'
        )}
      >
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            Finance
          </h1>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            Track expenses with AI
          </p>
        </div>

        {/* OAuth buttons */}
        <div className="space-y-3">
          <button
            onClick={handleGoogleSignIn}
            disabled={loading !== null}
            className={cn(
              'flex w-full items-center justify-center gap-3',
              'h-10 rounded-md px-4',
              'bg-neutral-50 dark:bg-neutral-800',
              'border border-neutral-200 dark:border-neutral-700',
              'text-neutral-900 dark:text-neutral-100 text-sm font-medium',
              'hover:bg-neutral-100 dark:hover:bg-neutral-700',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors'
            )}
          >
            {loading === 'google' ? (
              <Spinner size="sm" />
            ) : (
              <svg className="h-4 w-4" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
            )}
            Continue with Google
          </button>

          <button
            onClick={handleGithubSignIn}
            disabled={loading !== null}
            className={cn(
              'flex w-full items-center justify-center gap-3',
              'h-10 rounded-md px-4',
              'bg-neutral-900 dark:bg-neutral-100',
              'text-white dark:text-neutral-900 text-sm font-medium',
              'hover:opacity-90',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-opacity'
            )}
          >
            {loading === 'github' ? (
              <Spinner size="sm" />
            ) : (
              <Github className="h-4 w-4" />
            )}
            Continue with GitHub
          </button>
        </div>

        {/* Divider */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-800" />
          <span className="text-xs text-neutral-400 dark:text-neutral-500">or</span>
          <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-800" />
        </div>

        {/* Email form */}
        <form onSubmit={handleEmailSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={cn(
              'w-full h-10 rounded-md px-3',
              'bg-neutral-50 dark:bg-neutral-800',
              'border border-neutral-200 dark:border-neutral-700',
              'text-neutral-900 dark:text-neutral-100 text-sm',
              'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
              'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600',
              'transition-colors'
            )}
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className={cn(
              'w-full h-10 rounded-md px-3',
              'bg-neutral-50 dark:bg-neutral-800',
              'border border-neutral-200 dark:border-neutral-700',
              'text-neutral-900 dark:text-neutral-100 text-sm',
              'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
              'focus:outline-none focus:border-neutral-400 dark:focus:border-neutral-600',
              'transition-colors'
            )}
          />

          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading !== null}
            className={cn(
              'flex w-full items-center justify-center gap-2',
              'h-10 rounded-md px-4',
              'bg-neutral-900 dark:bg-neutral-100',
              'text-white dark:text-neutral-900 text-sm font-medium',
              'hover:opacity-90',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-opacity'
            )}
          >
            {loading === 'email' ? (
              <Spinner size="sm" />
            ) : (
              <>
                {isSignUp ? 'Create account' : 'Sign in'}
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        {/* Toggle sign up / sign in */}
        <p className="mt-6 text-center text-sm text-neutral-500 dark:text-neutral-400">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-neutral-900 dark:text-neutral-100 font-medium hover:underline"
          >
            {isSignUp ? 'Sign in' : 'Sign up'}
          </button>
        </p>
      </div>
    </div>
  )
}
