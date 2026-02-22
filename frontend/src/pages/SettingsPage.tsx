import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/utils/cn'
import { CategoriesTab } from '@/components/settings/CategoriesTab'
import { AppearanceTab } from '@/components/settings/AppearanceTab'
import { ProfileTab } from '@/components/settings/ProfileTab'
import { AIModelTab } from '@/components/settings/AIModelTab'
import { Tag, Palette, User, Cpu } from 'lucide-react'

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'categories', label: 'Categories', icon: Tag },
  { id: 'ai-model', label: 'AI Model', icon: Cpu },
] as const

type TabId = typeof tabs[number]['id']

const contentVariants = {
  enter: (direction: number) => ({ opacity: 0, y: direction * 20 }),
  center: { opacity: 1, y: 0 },
  exit: (direction: number) => ({ opacity: 0, y: direction * -20 }),
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile')
  const [direction, setDirection] = useState(0)

  const handleTabChange = (newTab: TabId) => {
    const currentIndex = tabs.findIndex(t => t.id === activeTab)
    const newIndex = tabs.findIndex(t => t.id === newTab)
    setDirection(newIndex > currentIndex ? 1 : -1)
    setActiveTab(newTab)
  }

  return (
    <div className="min-h-[calc(100dvh-3.5rem)] bg-[var(--bg-primary)]">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-xl font-semibold text-[var(--text-primary)] mb-6">
          Settings
        </h1>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Sidebar navigation */}
          <nav className="sm:w-48 flex-shrink-0">
            <ul className="flex sm:flex-col gap-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <li key={tab.id} className="relative">
                    {isActive && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute inset-0 bg-[var(--surface-primary)] rounded-lg shadow-sm border border-[var(--border-primary)]"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                      />
                    )}
                    <button
                      onClick={() => handleTabChange(tab.id)}
                      className={cn(
                        'relative w-full flex items-center gap-2 px-3 py-2',
                        'text-sm font-medium rounded-lg transition-colors',
                        isActive
                          ? 'text-[var(--text-primary)]'
                          : 'text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  </li>
                )
              })}
            </ul>
          </nav>

          {/* Content area */}
          <div className="flex-1 min-w-0">
            <div className="bg-[var(--surface-primary)] rounded-xl border border-[var(--border-primary)] p-4 sm:p-6 overflow-hidden">
              <AnimatePresence mode="wait" initial={false} custom={direction}>
                <motion.div
                  key={activeTab}
                  custom={direction}
                  variants={contentVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.2 }}
                >
                  {activeTab === 'profile' && <ProfileTab />}
                  {activeTab === 'appearance' && <AppearanceTab />}
                  {activeTab === 'categories' && <CategoriesTab />}
                  {activeTab === 'ai-model' && <AIModelTab />}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
