import { cn } from '@/utils/cn'
import { X } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
  title?: string
  className?: string
  glass?: boolean
}

export function Modal({ isOpen, onClose, children, title, className, glass = false }: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className={cn(
            'relative w-full max-w-md',
            'rounded-lg',
            glass
              ? 'glass-effect'
              : 'bg-[var(--surface-primary)] border border-[var(--border-primary)]',
            'shadow-lg',
            className
          )}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? 'modal-title' : undefined}
        >
          {title && (
            <div className="flex items-center justify-between border-b border-[var(--border-primary)] px-5 py-4">
              <h2
                id="modal-title"
                className="text-sm font-medium text-[var(--text-primary)]"
              >
                {title}
              </h2>
              <button
                onClick={onClose}
                className={cn(
                  'rounded p-1',
                  'text-[var(--text-muted)] hover:text-[var(--text-secondary)]',
                  'hover:bg-[var(--surface-hover)]',
                  'transition-colors'
                )}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          <div className="p-5 overflow-y-auto max-h-[70vh]">
            {children}
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}
