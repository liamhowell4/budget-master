import { cn } from '@/utils/cn'
import type { ReactNode } from 'react'

interface GlowContainerProps {
  children: ReactNode
  className?: string
  glowOnHover?: boolean
  glowAlways?: boolean
  as?: 'div' | 'button' | 'form'
}

/**
 * Container with Apple Intelligence gradient glow effect
 * - glowOnHover: soft glow appears on hover
 * - glowAlways: constant subtle glow
 */
export function GlowContainer({
  children,
  className,
  glowOnHover = false,
  glowAlways = false,
  as: Component = 'div',
}: GlowContainerProps) {
  return (
    <Component className={cn('group relative', className)}>
      {/* Gradient border layer */}
      <div className="absolute inset-0 rounded-2xl p-[1.5px] glow-gradient">
        <div className="h-full w-full rounded-2xl bg-light-bg dark:bg-dark-bg" />
      </div>

      {/* Glow effect layer (blurred) */}
      <div
        className={cn(
          'absolute -inset-1 rounded-2xl glow-gradient blur-xl transition-opacity duration-300',
          glowAlways ? 'opacity-40' : 'opacity-0',
          glowOnHover && 'group-hover:opacity-30'
        )}
      />

      {/* Content layer */}
      <div className="relative rounded-2xl bg-light-bg dark:bg-dark-bg">
        {children}
      </div>
    </Component>
  )
}
