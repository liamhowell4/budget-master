import { cn } from '@/utils/cn'
import * as LucideIcons from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState, useMemo } from 'react'

// Common icons for expense categories
const CATEGORY_ICONS = [
  'utensils',
  'coffee',
  'shopping-cart',
  'home',
  'zap',
  'heart-pulse',
  'fuel',
  'car',
  'car-taxi-front',
  'bed',
  'laptop',
  'plane',
  'more-horizontal',
  'circle',
  'wallet',
  'credit-card',
  'banknote',
  'piggy-bank',
  'gift',
  'shirt',
  'scissors',
  'dumbbell',
  'music',
  'film',
  'gamepad-2',
  'book',
  'graduation-cap',
  'baby',
  'dog',
  'cat',
  'leaf',
  'flower-2',
  'wrench',
  'hammer',
  'paintbrush',
  'smartphone',
  'monitor',
  'headphones',
  'camera',
  'bike',
  'bus',
  'train',
  'ship',
  'umbrella',
  'sun',
  'cloud',
  'snowflake',
  'wine',
  'beer',
  'ice-cream',
  'pizza',
  'apple',
  'egg',
  'fish',
  'salad',
  'sandwich',
  'soup',
  'cake',
  'cookie',
  'candy',
  'pill',
  'syringe',
  'stethoscope',
  'thermometer',
  'activity',
  'briefcase',
  'building',
  'store',
  'shopping-bag',
  'package',
  'box',
  'archive',
  'folder',
  'file-text',
  'receipt',
  'calculator',
]

// Convert kebab-case to PascalCase for Lucide
function toPascalCase(str: string): string {
  return str
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join('')
}

interface IconPickerProps {
  value: string
  onChange: (icon: string) => void
  className?: string
}

export function IconPicker({ value, onChange, className }: IconPickerProps) {
  const [search, setSearch] = useState('')

  const filteredIcons = useMemo(() => {
    if (!search.trim()) return CATEGORY_ICONS
    const searchLower = search.toLowerCase()
    return CATEGORY_ICONS.filter((icon) => icon.toLowerCase().includes(searchLower))
  }, [search])

  return (
    <div className={cn('space-y-3', className)}>
      <input
        type="text"
        placeholder="Search icons..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className={cn(
          'w-full px-3 py-2 text-sm',
          'rounded-lg border',
          'bg-white dark:bg-neutral-900',
          'border-neutral-200 dark:border-neutral-700',
          'text-neutral-900 dark:text-neutral-100',
          'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
          'focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500'
        )}
      />

      <div className="grid grid-cols-8 gap-1 max-h-48 overflow-y-auto p-1">
        {filteredIcons.map((iconName) => {
          const pascalName = toPascalCase(iconName)
          const Icon = (LucideIcons as unknown as Record<string, LucideIcon>)[pascalName]

          if (!Icon) return null

          return (
            <button
              key={iconName}
              type="button"
              onClick={() => onChange(iconName)}
              className={cn(
                'p-2 rounded-lg transition-colors',
                'flex items-center justify-center',
                value === iconName
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 ring-2 ring-blue-500'
                  : 'hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
              )}
              title={iconName}
            >
              <Icon className="h-5 w-5" />
            </button>
          )
        })}
      </div>

      {filteredIcons.length === 0 && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
          No icons found
        </p>
      )}
    </div>
  )
}

// Helper component to render an icon by name
interface DynamicIconProps {
  name: string
  className?: string
  style?: React.CSSProperties
}

export function DynamicIcon({ name, className, style }: DynamicIconProps) {
  const pascalName = toPascalCase(name)
  const Icon = (LucideIcons as unknown as Record<string, LucideIcon>)[pascalName]

  if (!Icon) {
    return <LucideIcons.Circle className={className} style={style} />
  }

  return <Icon className={className} style={style} />
}
