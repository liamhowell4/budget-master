import {
  Utensils,
  Coffee,
  ShoppingCart,
  Home,
  Lightbulb,
  HeartPulse,
  Fuel,
  Car,
  Bed,
  Laptop,
  Plane,
  Package,
  type LucideIcon,
} from 'lucide-react'
import * as LucideIcons from 'lucide-react'

// Legacy icon map for hardcoded ExpenseType categories
const iconMap: Record<string, LucideIcon> = {
  FOOD_OUT: Utensils,
  COFFEE: Coffee,
  GROCERIES: ShoppingCart,
  RENT: Home,
  UTILITIES: Lightbulb,
  MEDICAL: HeartPulse,
  GAS: Fuel,
  RIDE_SHARE: Car,
  HOTEL: Bed,
  TECH: Laptop,
  TRAVEL: Plane,
  OTHER: Package,
}

// Convert kebab-case to PascalCase for Lucide
function toPascalCase(str: string): string {
  return str
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join('')
}

interface CategoryIconProps {
  category: string
  iconName?: string // For custom categories with icon name
  className?: string
  style?: React.CSSProperties
}

export function CategoryIcon({ category, iconName, className, style }: CategoryIconProps) {
  // If iconName is provided (custom category), use dynamic icon lookup
  if (iconName) {
    const pascalName = toPascalCase(iconName)
    const DynamicIcon = (LucideIcons as unknown as Record<string, LucideIcon>)[pascalName]
    if (DynamicIcon) {
      return <DynamicIcon className={className} style={style} />
    }
  }

  // Fallback to legacy icon map for ExpenseType
  const Icon = iconMap[category] || Package
  return <Icon className={className} style={style} />
}
