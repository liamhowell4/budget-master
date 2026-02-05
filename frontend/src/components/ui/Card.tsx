import { cn } from '@/utils/cn'
import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
  variant?: 'default' | 'glass' | 'liquid'
  /** @deprecated Use variant="glass" instead */
  glass?: boolean
}

export function Card({
  children,
  className,
  padding = 'md',
  hover = false,
  variant = 'default',
  glass = false
}: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  }

  // Support legacy glass prop
  const effectiveVariant = glass ? 'glass' : variant

  const variantClasses = {
    default: 'bg-[var(--surface-primary)] border border-[var(--border-primary)]',
    glass: 'glass-effect',
    liquid: 'liquid-glass-card',
  }

  return (
    <div
      className={cn(
        'rounded-lg',
        variantClasses[effectiveVariant],
        hover && effectiveVariant === 'default' && 'transition-colors hover:bg-[var(--surface-hover)] cursor-pointer',
        hover && effectiveVariant === 'glass' && 'transition-all hover:bg-[var(--surface-hover)] cursor-pointer',
        hover && effectiveVariant === 'liquid' && 'transition-all cursor-pointer hover:shadow-lg',
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function CardHeader({ title, description, action, className }: CardHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between', className)}>
      <div>
        <h3 className="text-sm font-medium text-[var(--text-primary)]">
          {title}
        </h3>
        {description && (
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            {description}
          </p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
