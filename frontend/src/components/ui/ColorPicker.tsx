import { cn } from '@/utils/cn'

// Predefined color palette for categories
const CATEGORY_COLORS = [
  '#EF4444', // Red
  '#F97316', // Orange
  '#F59E0B', // Amber
  '#84CC16', // Lime
  '#22C55E', // Green
  '#14B8A6', // Teal
  '#06B6D4', // Cyan
  '#3B82F6', // Blue
  '#6366F1', // Indigo
  '#8B5CF6', // Violet
  '#A855F7', // Purple
  '#EC4899', // Pink
  '#F43F5E', // Rose
  '#92400E', // Brown
  '#6B7280', // Gray
  '#1F2937', // Dark Gray
]

interface ColorPickerProps {
  value: string
  onChange: (color: string) => void
  className?: string
}

export function ColorPicker({ value, onChange, className }: ColorPickerProps) {
  return (
    <div className={cn('space-y-3', className)}>
      <div className="grid grid-cols-8 gap-2">
        {CATEGORY_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            onClick={() => onChange(color)}
            className={cn(
              'h-8 w-8 rounded-lg transition-transform',
              'hover:scale-110',
              value === color && 'ring-2 ring-offset-2 ring-offset-white dark:ring-offset-neutral-900'
            )}
            style={{
              backgroundColor: color,
              // @ts-expect-error ringColor is a valid CSS custom property
              '--tw-ring-color': color,
            }}
            title={color}
          />
        ))}
      </div>

      {/* Custom color input */}
      <div className="flex items-center gap-2">
        <label className="text-sm text-neutral-500 dark:text-neutral-400">Custom:</label>
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-8 w-12 rounded cursor-pointer border border-neutral-200 dark:border-neutral-700"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => {
            const val = e.target.value
            if (/^#[0-9A-Fa-f]{0,6}$/.test(val)) {
              onChange(val)
            }
          }}
          placeholder="#FFFFFF"
          className={cn(
            'w-24 px-2 py-1 text-sm',
            'rounded border',
            'bg-white dark:bg-neutral-900',
            'border-neutral-200 dark:border-neutral-700',
            'text-neutral-900 dark:text-neutral-100',
            'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
          )}
        />
      </div>
    </div>
  )
}
