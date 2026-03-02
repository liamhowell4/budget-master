import { Modal } from '@/components/ui/Modal'
import { IncomePlannerStep } from '@/components/onboarding/IncomePlannerStep'

interface BudgetCalculatorModalProps {
  open: boolean
  onClose: () => void
  onApply: (amount: number) => void
}

export function BudgetCalculatorModal({ open, onClose, onApply }: BudgetCalculatorModalProps) {
  const handleApply = (amount: number) => {
    onApply(amount)
    onClose()
  }

  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title="Budget Calculator"
      className="max-w-lg"
    >
      <IncomePlannerStep onApply={handleApply} onSkip={onClose} />
    </Modal>
  )
}
