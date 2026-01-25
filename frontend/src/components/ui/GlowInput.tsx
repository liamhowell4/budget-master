import { cn } from '@/utils/cn'
import { forwardRef, type InputHTMLAttributes } from 'react'

interface GlowInputProps extends InputHTMLAttributes<HTMLInputElement> {
  className?: string
  containerClassName?: string
}

/**
 * Input with Apple Intelligence gradient glow effects
 * - Hover: soft diffused glow
 * - Focus: solid gradient border
 */
export const GlowInput = forwardRef<HTMLInputElement, GlowInputProps>(
  ({ className, containerClassName, ...props }, ref) => {
    return (
      <div className={cn('group relative', containerClassName)}>
        {/* Hover glow (soft diffused) */}
        <div
          className={cn(
            'absolute -inset-0.5 rounded-xl glow-gradient',
            'opacity-0 blur-md transition-opacity duration-300',
            'group-hover:opacity-30'
          )}
        />

        {/* Focus glow (solid gradient border) */}
        <div
          className={cn(
            'absolute -inset-0.5 rounded-xl glow-gradient',
            'opacity-0 transition-opacity duration-200',
            'group-focus-within:opacity-100'
          )}
        />

        {/* Input */}
        <input
          ref={ref}
          className={cn(
            'relative w-full rounded-xl px-4 py-3',
            'bg-light-surface dark:bg-dark-surface',
            'border border-light-border dark:border-dark-border',
            'text-gray-900 dark:text-gray-100',
            'placeholder:text-gray-500 dark:placeholder:text-gray-400',
            'focus:outline-none focus:border-transparent',
            'transition-all duration-200',
            className
          )}
          {...props}
        />
      </div>
    )
  }
)

GlowInput.displayName = 'GlowInput'
