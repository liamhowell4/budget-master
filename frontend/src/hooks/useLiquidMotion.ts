import { useEffect, useCallback, useRef } from 'react'

interface LiquidMotionOptions {
  /** Element ref to apply motion effect to */
  elementRef: React.RefObject<HTMLElement>
  /** Sensitivity of motion response (0-1, default 0.5) */
  sensitivity?: number
  /** Whether to use device orientation on mobile */
  useDeviceOrientation?: boolean
  /** Whether the effect is enabled */
  enabled?: boolean
}

/**
 * Hook to add motion-responsive shine to liquid glass elements.
 * Updates CSS custom properties based on mouse position or device tilt.
 *
 * Usage:
 * ```tsx
 * const ref = useRef<HTMLDivElement>(null)
 * useLiquidMotion({ elementRef: ref, enabled: isLiquidTheme })
 *
 * return <div ref={ref} className="liquid-glass-motion">...</div>
 * ```
 */
export function useLiquidMotion({
  elementRef,
  sensitivity = 0.5,
  useDeviceOrientation = true,
  enabled = true,
}: LiquidMotionOptions) {
  const rafRef = useRef<number | undefined>(undefined)
  const lastUpdateRef = useRef<number>(0)

  const updateShinePosition = useCallback(
    (x: number, y: number, intensity: number = 0.5) => {
      if (!elementRef.current) return

      // Throttle updates to 60fps
      const now = performance.now()
      if (now - lastUpdateRef.current < 16) return
      lastUpdateRef.current = now

      const el = elementRef.current
      el.style.setProperty('--shine-x', `${x}%`)
      el.style.setProperty('--shine-y', `${y}%`)
      el.style.setProperty('--shine-intensity', String(intensity))
    },
    [elementRef]
  )

  // Mouse move handler
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!elementRef.current || !enabled) return

      const rect = elementRef.current.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width) * 100
      const y = ((e.clientY - rect.top) / rect.height) * 100

      // Clamp and apply sensitivity
      const clampedX = Math.max(0, Math.min(100, x))
      const clampedY = Math.max(0, Math.min(100, y))

      // Calculate intensity based on distance from center
      const distFromCenter = Math.sqrt(
        Math.pow(clampedX - 50, 2) + Math.pow(clampedY - 50, 2)
      )
      const intensity = 0.3 + (distFromCenter / 70) * sensitivity

      rafRef.current = requestAnimationFrame(() => {
        updateShinePosition(clampedX, clampedY, Math.min(0.8, intensity))
      })
    },
    [elementRef, enabled, sensitivity, updateShinePosition]
  )

  // Mouse leave handler - reset to default
  const handleMouseLeave = useCallback(() => {
    if (!enabled) return
    updateShinePosition(50, 0, 0.4)
  }, [enabled, updateShinePosition])

  // Device orientation handler (mobile)
  const handleDeviceOrientation = useCallback(
    (e: DeviceOrientationEvent) => {
      if (!elementRef.current || !enabled || !useDeviceOrientation) return

      // gamma: left/right tilt (-90 to 90)
      // beta: front/back tilt (-180 to 180)
      const gamma = e.gamma || 0
      const beta = e.beta || 0

      // Convert to percentage (0-100)
      const x = 50 + (gamma / 90) * 50 * sensitivity
      const y = 50 + ((beta - 45) / 90) * 50 * sensitivity

      const clampedX = Math.max(0, Math.min(100, x))
      const clampedY = Math.max(0, Math.min(100, y))

      // Calculate intensity based on tilt amount
      const tiltAmount = Math.sqrt(gamma * gamma + (beta - 45) * (beta - 45))
      const intensity = 0.3 + (tiltAmount / 90) * sensitivity

      rafRef.current = requestAnimationFrame(() => {
        updateShinePosition(clampedX, clampedY, Math.min(0.7, intensity))
      })
    },
    [elementRef, enabled, sensitivity, useDeviceOrientation, updateShinePosition]
  )

  useEffect(() => {
    if (!enabled) return

    const element = elementRef.current
    if (!element) return

    // Add mouse listeners
    element.addEventListener('mousemove', handleMouseMove)
    element.addEventListener('mouseleave', handleMouseLeave)

    // Add device orientation listener if available and requested
    if (useDeviceOrientation && 'DeviceOrientationEvent' in window) {
      // Request permission on iOS 13+
      const requestPermission = async () => {
        if (
          typeof (DeviceOrientationEvent as any).requestPermission === 'function'
        ) {
          try {
            const permission = await (DeviceOrientationEvent as any).requestPermission()
            if (permission === 'granted') {
              window.addEventListener('deviceorientation', handleDeviceOrientation)
            }
          } catch {
            // Permission denied or error
          }
        } else {
          // Non-iOS or older iOS
          window.addEventListener('deviceorientation', handleDeviceOrientation)
        }
      }

      requestPermission()
    }

    return () => {
      element.removeEventListener('mousemove', handleMouseMove)
      element.removeEventListener('mouseleave', handleMouseLeave)
      window.removeEventListener('deviceorientation', handleDeviceOrientation)
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
      }
    }
  }, [
    elementRef,
    enabled,
    handleMouseMove,
    handleMouseLeave,
    handleDeviceOrientation,
    useDeviceOrientation,
  ])
}

/**
 * Simpler hook that just tracks global mouse position
 * and returns values that can be applied to any element.
 */
export function useGlobalLiquidMotion(enabled: boolean = true) {
  const positionRef = useRef({ x: 50, y: 50, intensity: 0.4 })

  useEffect(() => {
    if (!enabled) return

    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 100
      const y = (e.clientY / window.innerHeight) * 100

      positionRef.current = {
        x,
        y,
        intensity: 0.4 + Math.abs(x - 50) / 100 + Math.abs(y - 50) / 100,
      }

      // Update CSS custom properties on root
      document.documentElement.style.setProperty('--global-shine-x', `${x}%`)
      document.documentElement.style.setProperty('--global-shine-y', `${y}%`)
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [enabled])

  return positionRef.current
}
