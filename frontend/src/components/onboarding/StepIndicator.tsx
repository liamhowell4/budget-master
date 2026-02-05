import { cn } from '@/utils/cn'
import { motion } from 'framer-motion'

interface StepIndicatorProps {
  currentStep: number
  totalSteps: number
}

export function StepIndicator({ currentStep, totalSteps }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: totalSteps }, (_, i) => (
        <motion.div
          key={i}
          initial={false}
          animate={{
            scale: i === currentStep ? 1 : 0.8,
            backgroundColor: i === currentStep
              ? 'rgb(59, 130, 246)' // blue-500
              : i < currentStep
              ? 'rgb(34, 197, 94)' // green-500 (completed)
              : 'rgb(209, 213, 219)', // gray-300
          }}
          transition={{ duration: 0.2 }}
          className={cn(
            'w-2 h-2 rounded-full',
            i < currentStep && 'dark:bg-green-400',
            i === currentStep && 'dark:bg-blue-400',
            i > currentStep && 'dark:bg-neutral-600'
          )}
        />
      ))}
    </div>
  )
}
