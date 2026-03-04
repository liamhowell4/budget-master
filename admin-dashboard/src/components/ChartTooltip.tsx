import type { CSSProperties, ReactNode } from 'react'

/**
 * Shared tooltip that floats above the cursor, clamped within the chart.
 *
 * Usage:
 *   <Tooltip
 *     wrapperStyle={TOOLTIP_WRAPPER}
 *     allowEscapeViewBox={{ x: true, y: true }}
 *     content={(props) => (
 *       <FloatingTooltip {...props}>
 *         <div>your content</div>
 *       </FloatingTooltip>
 *     )}
 *   />
 */

/** Neutralize Recharts' wrapper so we control positioning ourselves. */
export const TOOLTIP_WRAPPER: CSSProperties = {
  transform: 'none',
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  pointerEvents: 'none',
  overflow: 'visible',
}

const BOX: CSSProperties = {
  background: '#111827e6',
  border: '1px solid #374151',
  color: '#f9fafb',
  backdropFilter: 'blur(4px)',
  fontSize: 12,
  padding: '6px 10px',
  borderRadius: 6,
  whiteSpace: 'nowrap',
  pointerEvents: 'none',
  position: 'absolute',
}

interface Props {
  active?: boolean
  coordinate?: { x: number; y: number }
  viewBox?: { x: number; y: number; width: number; height: number }
  children: ReactNode
}

export function FloatingTooltip({ active, coordinate, viewBox, children }: Props) {
  if (!active || !coordinate) return null

  const chartLeft = viewBox?.x ?? 0
  const chartWidth = viewBox?.width ?? 600
  const gap = 12

  // Clamp X: try to center on cursor, but stay within chart bounds
  // We use a ref callback to adjust after measuring, but as a good default
  // just set left to cursor X and use transform to center
  return (
    <div
      ref={(el) => {
        if (!el) return
        const w = el.offsetWidth
        // Center on cursor X
        let left = coordinate.x - w / 2
        // Clamp to chart area
        if (left < chartLeft) left = chartLeft
        if (left + w > chartLeft + chartWidth) left = chartLeft + chartWidth - w
        // Position above cursor
        let top = coordinate.y - gap - el.offsetHeight
        if (top < 0) top = coordinate.y + gap // flip below if at very top
        el.style.left = `${left}px`
        el.style.top = `${top}px`
      }}
      style={{ ...BOX, left: coordinate.x, top: coordinate.y - gap }}
    >
      {children}
    </div>
  )
}
