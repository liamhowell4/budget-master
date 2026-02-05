import { useState } from 'react'
import { cn } from '@/utils/cn'
import { useAuth } from '@/contexts/AuthContext'
import { updateDisplayName, updatePassword, getAuthProvider } from '@/lib/firebase'
import { User, Mail, Lock, Check, AlertCircle, Loader2 } from 'lucide-react'

export function ProfileTab() {
  const { user } = useAuth()
  const authProvider = getAuthProvider(user)
  const isEmailUser = authProvider === 'email'

  const [displayName, setDisplayName] = useState(user?.displayName || '')
  const [nameLoading, setNameLoading] = useState(false)
  const [nameSuccess, setNameSuccess] = useState(false)
  const [nameError, setNameError] = useState('')

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState(false)
  const [passwordError, setPasswordError] = useState('')

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!displayName.trim()) return

    setNameLoading(true)
    setNameError('')
    setNameSuccess(false)

    try {
      await updateDisplayName(displayName.trim())
      setNameSuccess(true)
      setTimeout(() => setNameSuccess(false), 3000)
    } catch (err) {
      setNameError(err instanceof Error ? err.message : 'Failed to update name')
    } finally {
      setNameLoading(false)
    }
  }

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess(false)

    if (newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters')
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }

    setPasswordLoading(true)

    try {
      await updatePassword(currentPassword, newPassword)
      setPasswordSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPasswordSuccess(false), 3000)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update password'
      if (message.includes('wrong-password') || message.includes('invalid-credential')) {
        setPasswordError('Current password is incorrect')
      } else {
        setPasswordError(message)
      }
    } finally {
      setPasswordLoading(false)
    }
  }

  const getProviderLabel = () => {
    switch (authProvider) {
      case 'google': return 'Google'
      case 'github': return 'GitHub'
      case 'email': return 'Email & Password'
      default: return 'Unknown'
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-medium text-[var(--text-primary)] mb-1">
          Profile
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          Manage your account settings
        </p>
      </div>

      {/* Account Info */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">
          Account Information
        </h3>

        <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--surface-secondary)]">
          <Mail className="h-4 w-4 text-[var(--text-muted)]" />
          <div>
            <p className="text-xs text-[var(--text-muted)]">Email</p>
            <p className="text-sm text-[var(--text-primary)]">{user?.email}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--surface-secondary)]">
          <Lock className="h-4 w-4 text-[var(--text-muted)]" />
          <div>
            <p className="text-xs text-[var(--text-muted)]">Sign-in Method</p>
            <p className="text-sm text-[var(--text-primary)]">{getProviderLabel()}</p>
          </div>
        </div>
      </div>

      {/* Display Name */}
      <form onSubmit={handleUpdateName} className="space-y-4">
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">
          Display Name
        </h3>

        <div className="flex gap-3">
          <div className="relative flex-1">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Enter your name"
              className={cn(
                'w-full pl-10 pr-3 py-2 rounded-lg',
                'bg-[var(--surface-secondary)] border border-[var(--border-primary)]',
                'text-sm text-[var(--text-primary)]',
                'placeholder:text-[var(--text-muted)]',
                'focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent'
              )}
            />
          </div>
          <button
            type="submit"
            disabled={nameLoading || !displayName.trim()}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-[var(--accent-primary)] text-white',
              'hover:bg-[var(--accent-hover)]',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center gap-2'
            )}
          >
            {nameLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : nameSuccess ? (
              <Check className="h-4 w-4" />
            ) : null}
            Save
          </button>
        </div>

        {nameError && (
          <div className="flex items-center gap-2 text-sm text-red-500">
            <AlertCircle className="h-4 w-4" />
            {nameError}
          </div>
        )}
        {nameSuccess && (
          <div className="flex items-center gap-2 text-sm text-green-500">
            <Check className="h-4 w-4" />
            Name updated successfully
          </div>
        )}
      </form>

      {/* Change Password - Only for email users */}
      {isEmailUser && (
        <form onSubmit={handleUpdatePassword} className="space-y-4">
          <h3 className="text-sm font-medium text-[var(--text-secondary)]">
            Change Password
          </h3>

          <div className="space-y-3">
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Current password"
                className={cn(
                  'w-full pl-10 pr-3 py-2 rounded-lg',
                  'bg-[var(--surface-secondary)] border border-[var(--border-primary)]',
                  'text-sm text-[var(--text-primary)]',
                  'placeholder:text-[var(--text-muted)]',
                  'focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent'
                )}
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="New password"
                className={cn(
                  'w-full pl-10 pr-3 py-2 rounded-lg',
                  'bg-[var(--surface-secondary)] border border-[var(--border-primary)]',
                  'text-sm text-[var(--text-primary)]',
                  'placeholder:text-[var(--text-muted)]',
                  'focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent'
                )}
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                className={cn(
                  'w-full pl-10 pr-3 py-2 rounded-lg',
                  'bg-[var(--surface-secondary)] border border-[var(--border-primary)]',
                  'text-sm text-[var(--text-primary)]',
                  'placeholder:text-[var(--text-muted)]',
                  'focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent'
                )}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={passwordLoading || !currentPassword || !newPassword || !confirmPassword}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-[var(--accent-primary)] text-white',
              'hover:bg-[var(--accent-hover)]',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center gap-2'
            )}
          >
            {passwordLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : passwordSuccess ? (
              <Check className="h-4 w-4" />
            ) : null}
            Update Password
          </button>

          {passwordError && (
            <div className="flex items-center gap-2 text-sm text-red-500">
              <AlertCircle className="h-4 w-4" />
              {passwordError}
            </div>
          )}
          {passwordSuccess && (
            <div className="flex items-center gap-2 text-sm text-green-500">
              <Check className="h-4 w-4" />
              Password updated successfully
            </div>
          )}
        </form>
      )}

      {!isEmailUser && (
        <div className="p-4 rounded-lg bg-[var(--surface-secondary)] border border-[var(--border-primary)]">
          <p className="text-sm text-[var(--text-muted)]">
            Password management is handled by {getProviderLabel()}. To change your password, please update it through your {getProviderLabel()} account settings.
          </p>
        </div>
      )}
    </div>
  )
}
