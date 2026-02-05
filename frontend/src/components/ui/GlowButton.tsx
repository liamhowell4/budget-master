import { cn } from '@/utils/cn'
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'

interface GlowButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

/**
 * Button with Apple Intelligence gradient glow effects
 * - Primary: gradient background with glow
 * - Secondary: border with hover glow
 * - Ghost: transparent with hover glow
 */
export const GlowButton = forwardRef<HTMLButtonElement, GlowButtonProps>(
  ({ children, variant = 'primary', size = 'md', className, ...props }, ref) => {
    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2.5 text-base',
      lg: 'px-6 py-3 text-lg',
    }

    if (variant === 'primary') {
      return (
        <div className="group relative inline-block">
          {/* Subtle glow effect */}
          <div
            className={cn(
              'absolute -inset-1 rounded-xl bg-blue-500 blur-lg',
              'opacity-0 transition-opacity duration-300',
              'group-hover:opacity-30',
              'group-active:opacity-40',
              props.disabled && 'group-hover:opacity-0'
            )}
          />
          <button
            ref={ref}
            className={cn(
              'relative rounded-xl font-medium',
              'bg-blue-600 hover:bg-blue-700 text-white',
              'transition-all duration-200',
              'active:scale-[0.98]',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600',
              sizeClasses[size],
              className
            )}
            {...props}
          >
            {children}
          </button>
        </div>
      )
    }

    if (variant === 'secondary') {
      return (
        <div className="group relative inline-block">
          {/* Hover glow */}
          <div
            className={cn(
              'absolute -inset-0.5 rounded-xl glow-gradient',
              'opacity-0 blur-md transition-opacity duration-300',
              'group-hover:opacity-40'
            )}
          />
          {/* Border gradient */}
          <div className="absolute inset-0 rounded-xl p-[1.5px] glow-gradient opacity-60 group-hover:opacity-100 transition-opacity">
            <div className="h-full w-full rounded-xl bg-light-bg dark:bg-dark-bg" />
          </div>
          <button
            ref={ref}
            className={cn(
              'relative rounded-xl font-medium',
              'bg-transparent',
              'text-gray-900 dark:text-gray-100',
              'transition-all duration-200',
              'active:scale-[0.98]',
              sizeClasses[size],
              className
            )}
            {...props}
          >
            {children}
          </button>
        </div>
      )
    }

    // Ghost variant
    return (
      <button
        ref={ref}
        className={cn(
          'relative rounded-xl font-medium',
          'bg-transparent',
          'text-gray-600 dark:text-gray-400',
          'hover:text-gray-900 dark:hover:text-gray-100',
          'hover:bg-gray-100 dark:hover:bg-white/5',
          'transition-all duration-200',
          'active:scale-[0.98]',
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {children}
      </button>
    )
  }
)

GlowButton.displayName = 'GlowButton'
