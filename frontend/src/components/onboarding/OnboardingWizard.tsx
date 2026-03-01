import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/utils/cn'
import { GlowButton } from '@/components/ui/GlowButton'
import { Spinner } from '@/components/ui/Spinner'
import { StepIndicator } from './StepIndicator'
import { WelcomeStep } from './WelcomeStep'
import { IncomePlannerStep } from './IncomePlannerStep'
import { TotalBudgetStep } from './TotalBudgetStep'
import { CategoriesStep, type CustomCategory } from './CategoriesStep'
import { CapsStep } from './CapsStep'
import { ExclusionsStep } from './ExclusionsStep'
import { ReviewStep } from './ReviewStep'
import { categoryService } from '@/services/categoryService'
import { ArrowLeft, X } from 'lucide-react'

type Step = 'welcome' | 'incomePlanner' | 'totalBudget' | 'categories' | 'caps' | 'exclusions' | 'review'

const STEPS: Step[] = ['welcome', 'incomePlanner', 'totalBudget', 'categories', 'caps', 'exclusions', 'review']

const contentVariants = {
  enter: (direction: number) => ({
    opacity: 0,
    x: direction > 0 ? 50 : -50,
  }),
  center: {
    opacity: 1,
    x: 0,
  },
  exit: (direction: number) => ({
    opacity: 0,
    x: direction > 0 ? -50 : 50,
  }),
}

interface OnboardingWizardProps {
  onComplete: () => void
  onSkip: () => void
}

export function OnboardingWizard({ onComplete, onSkip }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>('welcome')
  const [direction, setDirection] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Wizard state
  const [totalBudget, setTotalBudget] = useState(0)
  const [budgetError, setBudgetError] = useState<string | null>(null)
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<string[]>([])
  const [customCategories, setCustomCategories] = useState<CustomCategory[]>([])
  const [categoryCaps, setCategoryCaps] = useState<Record<string, number>>({})
  const [excludedCategoryIds, setExcludedCategoryIds] = useState<string[]>([])

  // Lock body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onSkip()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onSkip])

  const currentStepIndex = STEPS.indexOf(currentStep)

  const goToStep = (step: Step) => {
    const newIndex = STEPS.indexOf(step)
    setDirection(newIndex > currentStepIndex ? 1 : -1)
    setCurrentStep(step)
  }

  const goNext = () => {
    if (currentStep === 'totalBudget') {
      if (totalBudget <= 0) {
        setBudgetError('Please enter a budget greater than $0')
        return
      }
      setBudgetError(null)
    }

    const nextIndex = currentStepIndex + 1
    if (nextIndex < STEPS.length) {
      goToStep(STEPS[nextIndex])
    }
  }

  const goBack = () => {
    const prevIndex = currentStepIndex - 1
    if (prevIndex >= 0) {
      goToStep(STEPS[prevIndex])
    }
  }

  // IncomePlannerStep handlers
  const handleIncomePlannerApply = (amount: number) => {
    setTotalBudget(amount)
    setBudgetError(null)
    goToStep('totalBudget')
  }

  const handleIncomePlannerSkip = () => {
    goToStep('totalBudget')
  }

  // ExclusionsStep skip handler
  const handleExclusionsSkip = () => {
    goToStep('review')
  }

  const handleComplete = async () => {
    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const allCategoryIds = [
        ...selectedCategoryIds.filter((id) => id !== 'OTHER'),
        ...customCategories.map((c) => c.id),
      ]

      // Only include caps for categories that are currently selected
      const finalCaps: Record<string, number> = {}
      for (const catId of selectedCategoryIds) {
        const cap = categoryCaps[catId]
        if (cap && cap > 0) finalCaps[catId] = cap
      }
      // Also include custom category caps
      for (const custom of customCategories) {
        const cap = categoryCaps[custom.id]
        if (cap && cap > 0) finalCaps[custom.id] = cap
      }

      await categoryService.completeOnboarding({
        total_budget: totalBudget,
        selected_category_ids: allCategoryIds,
        category_caps: finalCaps,
        custom_categories: customCategories.map((c) => ({
          display_name: c.display_name,
          icon: c.icon,
          color: c.color,
          monthly_cap: categoryCaps[c.id] || 0,
        })),
        excluded_category_ids: excludedCategoryIds,
      })

      onComplete()
    } catch (err: unknown) {
      console.error('Error completing onboarding:', err)
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to save. Please try again.'
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const allocatedTotal = Object.values(categoryCaps).reduce((sum, cap) => sum + cap, 0)
  const isOverBudget = allocatedTotal > totalBudget

  const canProceed = () => {
    switch (currentStep) {
      case 'welcome':
        return true
      case 'incomePlanner':
        return true
      case 'totalBudget':
        return totalBudget > 0
      case 'categories':
        return selectedCategoryIds.length > 0 || customCategories.length > 0
      case 'caps':
        return !isOverBudget
      case 'exclusions':
        return true
      case 'review':
        return true
      default:
        return true
    }
  }

  const getButtonText = () => {
    switch (currentStep) {
      case 'welcome':
        return 'Get Started'
      case 'caps':
        return 'Continue'
      case 'exclusions':
        return 'Review'
      case 'review':
        return isSubmitting ? 'Setting Up...' : 'Complete Setup'
      default:
        return 'Continue'
    }
  }

  // Steps that manage their own navigation (no footer Next button)
  const selfNavigatingSteps: Step[] = ['incomePlanner']
  const isSelfNavigating = selfNavigatingSteps.includes(currentStep)

  return createPortal(
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Content */}
      <div className="relative flex h-full sm:min-h-full items-center justify-center p-0 sm:p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'w-full sm:max-w-2xl',
            'bg-white dark:bg-neutral-900',
            'rounded-none sm:rounded-2xl shadow-2xl',
            'border-0 sm:border border-neutral-200 dark:border-neutral-800',
            'overflow-hidden',
            'h-full sm:h-auto sm:max-h-[90vh]',
            'flex flex-col'
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-800">
            <button
              onClick={onSkip}
              className={cn(
                'text-sm text-neutral-500 dark:text-neutral-400',
                'hover:text-neutral-700 dark:hover:text-neutral-200',
                'transition-colors'
              )}
            >
              Skip
            </button>
            <StepIndicator currentStep={currentStepIndex} totalSteps={STEPS.length} />
            <button
              onClick={onSkip}
              className={cn(
                'p-1 rounded',
                'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                'transition-colors'
              )}
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Step Content */}
          <div className="p-6 min-h-[400px] flex-1 overflow-y-auto">
            <AnimatePresence mode="wait" initial={false} custom={direction}>
              <motion.div
                key={currentStep}
                custom={direction}
                variants={contentVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25, ease: 'easeInOut' }}
              >
                {currentStep === 'welcome' && <WelcomeStep />}
                {currentStep === 'incomePlanner' && (
                  <IncomePlannerStep
                    onApply={handleIncomePlannerApply}
                    onSkip={handleIncomePlannerSkip}
                  />
                )}
                {currentStep === 'totalBudget' && (
                  <TotalBudgetStep
                    value={totalBudget}
                    onChange={setTotalBudget}
                    error={budgetError || undefined}
                  />
                )}
                {currentStep === 'categories' && (
                  <CategoriesStep
                    selectedIds={selectedCategoryIds}
                    onChange={setSelectedCategoryIds}
                    customCategories={customCategories}
                    onCustomCategoriesChange={setCustomCategories}
                  />
                )}
                {currentStep === 'caps' && (
                  <CapsStep
                    totalBudget={totalBudget}
                    selectedCategoryIds={selectedCategoryIds}
                    customCategories={customCategories}
                    caps={categoryCaps}
                    onChange={setCategoryCaps}
                  />
                )}
                {currentStep === 'exclusions' && (
                  <ExclusionsStep
                    selectedCategoryIds={selectedCategoryIds}
                    customCategories={customCategories}
                    excludedCategoryIds={excludedCategoryIds}
                    onChange={setExcludedCategoryIds}
                    onSkip={handleExclusionsSkip}
                  />
                )}
                {currentStep === 'review' && (
                  <ReviewStep
                    totalBudget={totalBudget}
                    selectedCategoryIds={selectedCategoryIds}
                    customCategories={customCategories}
                    caps={categoryCaps}
                  />
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Error message */}
          {submitError && (
            <div className="px-6 pb-2">
              <p className="text-sm text-red-600 dark:text-red-400 text-center">
                {submitError}
              </p>
            </div>
          )}

          {/* Footer — hidden for self-navigating steps */}
          {!isSelfNavigating && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/50">
              <div>
                {currentStepIndex > 0 && (
                  <button
                    onClick={goBack}
                    disabled={isSubmitting}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-2 text-sm',
                      'text-neutral-600 dark:text-neutral-400',
                      'hover:text-neutral-900 dark:hover:text-neutral-100',
                      'disabled:opacity-50',
                      'transition-colors'
                    )}
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                  </button>
                )}
              </div>

              <div>
                {currentStep === 'review' ? (
                  <GlowButton
                    onClick={handleComplete}
                    disabled={!canProceed() || isSubmitting}
                  >
                    {isSubmitting ? (
                      <span className="flex items-center gap-2">
                        <Spinner size="sm" />
                        Setting Up...
                      </span>
                    ) : (
                      'Complete Setup'
                    )}
                  </GlowButton>
                ) : (
                  <GlowButton onClick={goNext} disabled={!canProceed()}>
                    {getButtonText()}
                  </GlowButton>
                )}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>,
    document.body
  )
}
