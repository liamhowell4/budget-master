import { useState } from 'react'
import { cn } from '@/utils/cn'
import { CategoriesTab } from '@/components/settings/CategoriesTab'
import { AppearanceTab } from '@/components/settings/AppearanceTab'
import { ProfileTab } from '@/components/settings/ProfileTab'
import { Tag, Palette, User } from 'lucide-react'

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'categories', label: 'Categories', icon: Tag },
] as const

type TabId = typeof tabs[number]['id']

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  return (
    <div className="min-h-[calc(100dvh-3.5rem)] bg-neutral-50 dark:bg-neutral-950">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6">
          Settings
        </h1>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Sidebar navigation */}
          <nav className="sm:w-48 flex-shrink-0">
            <ul className="flex sm:flex-col gap-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <li key={tab.id}>
                    <button
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'w-full flex items-center gap-2 px-3 py-2',
                        'text-sm font-medium rounded-lg transition-colors',
                        activeTab === tab.id
                          ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-sm border border-neutral-200 dark:border-neutral-800'
                          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-900'
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
            <div className="bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 sm:p-6">
              {activeTab === 'profile' && <ProfileTab />}
              {activeTab === 'appearance' && <AppearanceTab />}
              {activeTab === 'categories' && <CategoriesTab />}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
