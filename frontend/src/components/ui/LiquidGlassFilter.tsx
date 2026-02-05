/**
 * SVG Filters for Liquid Glass Refraction Effect
 *
 * This component renders hidden SVG filters that can be referenced
 * via CSS `backdrop-filter: url(#filter-id)`.
 *
 * NOTE: SVG backdrop filters only work in Chromium browsers (Chrome, Edge, Brave).
 * Other browsers will fall back to standard blur effects.
 *
 * Usage:
 * 1. Render <LiquidGlassFilter /> once in your app (e.g., in App.tsx)
 * 2. Apply the effect via CSS: `backdrop-filter: url(#liquid-refraction)`
 */
export function LiquidGlassFilter() {
  return (
    <svg
      style={{
        position: 'absolute',
        width: 0,
        height: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    >
      <defs>
        {/* Basic Liquid Glass Refraction Filter */}
        <filter id="liquid-refraction" colorInterpolationFilters="sRGB">
          {/* Step 1: Apply gaussian blur for frosted effect */}
          <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blurred" />

          {/* Step 2: Create turbulence for organic distortion */}
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.015"
            numOctaves="3"
            seed="42"
            result="noise"
          />

          {/* Step 3: Apply displacement for refraction effect */}
          <feDisplacementMap
            in="blurred"
            in2="noise"
            scale="8"
            xChannelSelector="R"
            yChannelSelector="G"
            result="displaced"
          />

          {/* Step 4: Boost saturation for vibrancy */}
          <feColorMatrix
            in="displaced"
            type="saturate"
            values="1.3"
            result="saturated"
          />

          {/* Step 5: Slight brightness boost */}
          <feComponentTransfer in="saturated" result="brightened">
            <feFuncR type="linear" slope="1.05" intercept="0.02" />
            <feFuncG type="linear" slope="1.05" intercept="0.02" />
            <feFuncB type="linear" slope="1.05" intercept="0.02" />
          </feComponentTransfer>
        </filter>

        {/* Subtle Refraction - less distortion for smaller elements */}
        <filter id="liquid-refraction-subtle" colorInterpolationFilters="sRGB">
          <feGaussianBlur in="SourceGraphic" stdDeviation="1" result="blurred" />
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.02"
            numOctaves="2"
            seed="123"
            result="noise"
          />
          <feDisplacementMap
            in="blurred"
            in2="noise"
            scale="4"
            xChannelSelector="R"
            yChannelSelector="G"
            result="displaced"
          />
          <feColorMatrix in="displaced" type="saturate" values="1.2" />
        </filter>

        {/* Strong Refraction - more dramatic for hero sections */}
        <filter id="liquid-refraction-strong" colorInterpolationFilters="sRGB">
          <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blurred" />
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.01"
            numOctaves="4"
            seed="789"
            result="noise"
          />
          <feDisplacementMap
            in="blurred"
            in2="noise"
            scale="15"
            xChannelSelector="R"
            yChannelSelector="G"
            result="displaced"
          />
          <feColorMatrix in="displaced" type="saturate" values="1.5" />
          <feComponentTransfer>
            <feFuncR type="linear" slope="1.1" intercept="0.02" />
            <feFuncG type="linear" slope="1.1" intercept="0.02" />
            <feFuncB type="linear" slope="1.1" intercept="0.02" />
          </feComponentTransfer>
        </filter>

        {/* Chromatic Aberration - rainbow fringing at edges (advanced) */}
        <filter id="liquid-chromatic" colorInterpolationFilters="sRGB">
          {/* Separate RGB channels */}
          <feColorMatrix
            type="matrix"
            values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"
            in="SourceGraphic"
            result="red"
          />
          <feColorMatrix
            type="matrix"
            values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0"
            in="SourceGraphic"
            result="green"
          />
          <feColorMatrix
            type="matrix"
            values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"
            in="SourceGraphic"
            result="blue"
          />

          {/* Create noise for displacement */}
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.015"
            numOctaves="2"
            result="noise"
          />

          {/* Displace each channel slightly differently */}
          <feDisplacementMap
            in="red"
            in2="noise"
            scale="6"
            xChannelSelector="R"
            yChannelSelector="G"
            result="red-displaced"
          />
          <feDisplacementMap
            in="green"
            in2="noise"
            scale="5"
            xChannelSelector="R"
            yChannelSelector="G"
            result="green-displaced"
          />
          <feDisplacementMap
            in="blue"
            in2="noise"
            scale="4"
            xChannelSelector="R"
            yChannelSelector="G"
            result="blue-displaced"
          />

          {/* Blur each channel */}
          <feGaussianBlur in="red-displaced" stdDeviation="1.2" result="red-blur" />
          <feGaussianBlur in="green-displaced" stdDeviation="1" result="green-blur" />
          <feGaussianBlur in="blue-displaced" stdDeviation="0.8" result="blue-blur" />

          {/* Recombine channels */}
          <feBlend mode="screen" in="red-blur" in2="green-blur" result="rg" />
          <feBlend mode="screen" in="rg" in2="blue-blur" result="rgb" />

          {/* Boost saturation */}
          <feColorMatrix in="rgb" type="saturate" values="1.4" />
        </filter>

        {/* Specular highlight gradient for manual application */}
        <linearGradient id="liquid-shine-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.6)" />
          <stop offset="50%" stopColor="rgba(255,255,255,0.1)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </linearGradient>

        {/* Radial shine for motion effects */}
        <radialGradient id="liquid-radial-shine" cx="50%" cy="30%" r="70%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.5)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
      </defs>
    </svg>
  )
}

export default LiquidGlassFilter
