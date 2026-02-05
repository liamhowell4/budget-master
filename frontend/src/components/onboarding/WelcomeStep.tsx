import { Wallet, MessageSquare, PieChart, Bell } from 'lucide-react'

const features = [
  {
    icon: MessageSquare,
    text: 'Chat naturally to log expenses - just say "Coffee $5"',
  },
  {
    icon: PieChart,
    text: 'Track spending by category with visual insights',
  },
  {
    icon: Bell,
    text: 'Get alerts when you\'re approaching budget limits',
  },
]

export function WelcomeStep() {
  return (
    <div className="text-center space-y-8">
      {/* Icon */}
      <div className="flex justify-center">
        <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20">
          <Wallet className="h-12 w-12 text-blue-500" />
        </div>
      </div>

      {/* Headline */}
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
          Welcome to Budget Master
        </h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Let's set up your budget in a few quick steps
        </p>
      </div>

      {/* Features */}
      <div className="space-y-4 text-left max-w-sm mx-auto">
        {features.map((feature, index) => {
          const Icon = feature.icon
          return (
            <div key={index} className="flex items-start gap-3">
              <div className="flex-shrink-0 p-2 rounded-lg bg-neutral-100 dark:bg-neutral-800">
                <Icon className="h-4 w-4 text-neutral-600 dark:text-neutral-400" />
              </div>
              <p className="text-sm text-neutral-600 dark:text-neutral-300 pt-1.5">
                {feature.text}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
