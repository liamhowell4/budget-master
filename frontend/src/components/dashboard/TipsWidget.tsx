import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { Card } from '@/components/ui/Card'
import {
  Plus,
  Pencil,
  BarChart2,
  RefreshCw,
  Wallet,
  ChevronDown,
  ChevronUp,
  ArrowRight,
} from 'lucide-react'

const STORAGE_KEY = 'tips_widget_expanded'

interface Tip {
  prompt: string
  preview: string
}

interface TipSection {
  icon: React.ElementType
  title: string
  tips: Tip[]
}

const SECTIONS: TipSection[] = [
  {
    icon: Plus,
    title: 'Logging expenses',
    tips: [
      {
        prompt: 'Chipotle $14.50 for lunch',
        preview: 'Got it! Logged Chipotle for $14.50 under Food Out.',
      },
      {
        prompt: 'Groceries $67 at Whole Foods',
        preview: 'Saved! $67.00 at Whole Foods added to Groceries.',
      },
      {
        prompt: 'Amazon order $34.99',
        preview: 'Added! Amazon Order for $34.99 under Tech.',
      },
      {
        prompt: 'Starbucks $5.75 this morning',
        preview: 'Logged $5.75 at Starbucks under Coffee.',
      },
    ],
  },
  {
    icon: Pencil,
    title: 'Editing and deleting',
    tips: [
      {
        prompt: 'Delete that last one',
        preview: 'Done — I have deleted the Starbucks expense.',
      },
      {
        prompt: 'Change that to $15',
        preview: 'Updated! Changed the amount to $15.00.',
      },
      {
        prompt: 'Actually it was Whole Foods, not Target',
        preview: 'Fixed! Updated the name to Whole Foods.',
      },
    ],
  },
  {
    icon: BarChart2,
    title: 'Analytics',
    tips: [
      {
        prompt: 'How much on food this month?',
        preview: 'You have spent $312.40 on Food Out this month ($87.60 remaining).',
      },
      {
        prompt: 'Compare this month to last',
        preview: 'This month: $1,204. Last month: $1,089. You are up $115 (+10.6%).',
      },
      {
        prompt: 'Show my top 5 expenses',
        preview: 'Your biggest this month: Rent ($1,400), Groceries ($187)...',
      },
      {
        prompt: 'Am I on track this month?',
        preview: 'At 18 days in, you have used 62% of your budget. You are slightly ahead of pace.',
      },
    ],
  },
  {
    icon: RefreshCw,
    title: 'Recurring expenses',
    tips: [
      {
        prompt: 'Add rent $1,400 every month',
        preview: 'Created! Rent ($1,400) will be added on the 1st each month.',
      },
      {
        prompt: 'List my recurring expenses',
        preview: 'You have 2 recurring expenses: Rent ($1,400/mo), Netflix ($15.99/mo).',
      },
      {
        prompt: 'Remove the Netflix recurring',
        preview: 'Done — Netflix recurring expense has been removed.',
      },
    ],
  },
  {
    icon: Wallet,
    title: 'Budget status',
    tips: [
      {
        prompt: "What's left in my dining budget?",
        preview: 'You have $87.60 remaining in Food Out (65% used, $312.40 spent).',
      },
      {
        prompt: "How's my total budget looking?",
        preview: 'You have used $1,204 of your $2,000 budget this month (60.2%).',
      },
      {
        prompt: 'Which category am I closest to going over?',
        preview: 'Food Out is closest at 87% used with $37 remaining.',
      },
    ],
  },
]

export function TipsWidget() {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(expanded))
    } catch {
      // ignore storage errors
    }
  }, [expanded])

  const handleTry = (prompt: string) => {
    navigate('/chat', { state: { prefillPrompt: prompt } })
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between mb-3 group"
        aria-expanded={expanded}
      >
        <h2 className="text-sm font-medium text-[var(--text-primary)]">
          What can I ask?
        </h2>
        <span className="flex items-center gap-1 text-xs text-[var(--text-muted)] group-hover:text-[var(--text-secondary)] transition-colors">
          {expanded ? (
            <>Collapse <ChevronUp className="h-3.5 w-3.5" /></>
          ) : (
            <>Expand <ChevronDown className="h-3.5 w-3.5" /></>
          )}
        </span>
      </button>

      {expanded && (
        <div className="space-y-4">
          {SECTIONS.map((section) => {
            const Icon = section.icon
            return (
              <Card key={section.title} padding="md">
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="h-4 w-4 text-[var(--text-muted)]" />
                  <h3 className="text-sm font-medium text-[var(--text-primary)]">
                    {section.title}
                  </h3>
                </div>
                <div className="space-y-2">
                  {section.tips.map((tip) => (
                    <div
                      key={tip.prompt}
                      className={cn(
                        'p-3 rounded-lg',
                        'bg-[var(--surface-secondary)]',
                        'border border-[var(--border-primary)]'
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-[var(--text-primary)] mb-0.5">
                            "{tip.prompt}"
                          </p>
                          <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                            {tip.preview}
                          </p>
                        </div>
                        <button
                          onClick={() => handleTry(tip.prompt)}
                          className={cn(
                            'flex items-center gap-1 px-2.5 py-1.5 rounded-md flex-shrink-0',
                            'text-xs font-medium',
                            'bg-[var(--surface-primary)]',
                            'border border-[var(--border-primary)]',
                            'text-[var(--text-secondary)]',
                            'hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]',
                            'transition-colors'
                          )}
                          aria-label={`Try: ${tip.prompt}`}
                        >
                          Try
                          <ArrowRight className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
