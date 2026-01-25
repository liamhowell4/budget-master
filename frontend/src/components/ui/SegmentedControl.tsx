import { useRef, useState, useEffect, useLayoutEffect, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface SegmentOption {
  value: string
  label: string
  badge?: ReactNode
}

interface SegmentedControlProps {
  options: SegmentOption[]
  value: string
  onChange: (value: string) => void
  className?: string
  size?: 'sm' | 'md'
}

export function SegmentedControl({
  options,
  value,
  onChange,
  className,
  size = 'md',
}: SegmentedControlProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const buttonRefs = useRef<Map<string, HTMLButtonElement>>(new Map())
  const [indicatorStyle, setIndicatorStyle] = useState<{ left: number; width: number } | null>(null)
  const hasMeasured = useRef(false)

  const measureButton = (buttonValue: string) => {
    const container = containerRef.current
    const button = buttonRefs.current.get(buttonValue)

    if (!container || !button) return null

    const containerRect = container.getBoundingClientRect()
    const buttonRect = button.getBoundingClientRect()

    return {
      left: buttonRect.left - containerRect.left,
      width: buttonRect.width,
    }
  }

  // Measure and update indicator position
  useLayoutEffect(() => {
    const measure = () => {
      const style = measureButton(value)
      if (style) {
        setIndicatorStyle(style)
        hasMeasured.current = true
      }
    }

    // Measure immediately and also after a frame for safety
    measure()
    const frame = requestAnimationFrame(measure)
    return () => cancelAnimationFrame(frame)
  }, [value])

  // Recalculate on resize
  useEffect(() => {
    const handleResize = () => {
      const style = measureButton(value)
      if (style) setIndicatorStyle(style)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [value])

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative inline-flex items-center rounded-full',
        'bg-neutral-100 dark:bg-neutral-800',
        size === 'sm' ? 'p-1' : 'p-1.5',
        className
      )}
    >
      {/* Animated pill indicator */}
      {indicatorStyle && (
        <div
          className={cn(
            'absolute left-0 rounded-full',
            'bg-white dark:bg-neutral-900',
            'shadow-sm',
            size === 'sm' ? 'top-1 bottom-1' : 'top-1.5 bottom-1.5',
            // Only animate after first measurement
            hasMeasured.current && 'transition-[transform,width] duration-200 ease-out'
          )}
          style={{
            transform: `translateX(${indicatorStyle.left}px)`,
            width: indicatorStyle.width,
          }}
        />
      )}

      {/* Tab buttons */}
      {options.map((option) => (
        <button
          key={option.value}
          ref={(el) => {
            if (el) buttonRefs.current.set(option.value, el)
          }}
          onClick={() => onChange(option.value)}
          className={cn(
            'relative z-10 flex items-center justify-center gap-2 rounded-full font-medium transition-colors',
            size === 'sm' ? 'px-4 py-1.5 text-sm' : 'px-5 py-2 text-sm',
            option.value === value
              ? 'text-neutral-900 dark:text-neutral-100'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'
          )}
        >
          {option.label}
          {option.badge}
        </button>
      ))}
    </div>
  )
}
