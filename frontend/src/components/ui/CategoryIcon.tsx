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
import type { ExpenseType } from '@/types/expense'

const iconMap: Record<ExpenseType, LucideIcon> = {
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

interface CategoryIconProps {
  category: ExpenseType
  className?: string
}

export function CategoryIcon({ category, className }: CategoryIconProps) {
  const Icon = iconMap[category] || Package
  return <Icon className={className} />
}
