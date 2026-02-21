import { useState, useEffect } from 'react'
import { cn } from '@/utils/cn'
import { Check, Loader2, AlertCircle } from 'lucide-react'
import {
  getUserSettings,
  updateUserSettings,
  type SupportedModel,
} from '@/services/userSettingsService'

interface ModelInfo {
  id: SupportedModel
  label: string
  description: string
}

interface ProviderGroup {
  provider: string
  models: ModelInfo[]
}

const MODEL_GROUPS: ProviderGroup[] = [
  {
    provider: 'Anthropic',
    models: [
      {
        id: 'claude-sonnet-4-6',
        label: 'Claude Sonnet 4.6',
        description: 'Balanced intelligence and speed',
      },
      {
        id: 'claude-haiku-4-5',
        label: 'Claude Haiku 4.5',
        description: 'Fast and compact',
      },
    ],
  },
  {
    provider: 'OpenAI',
    models: [
      {
        id: 'gpt-5-mini',
        label: 'GPT-5 Mini',
        description: 'Lightweight and efficient',
      },
      {
        id: 'gpt-5.1',
        label: 'GPT-5.1',
        description: 'High-capability reasoning',
      },
    ],
  },
  {
    provider: 'Google',
    models: [
      {
        id: 'gemini-3.1-pro',
        label: 'Gemini 3.1 Pro',
        description: 'Advanced multimodal model',
      },
      {
        id: 'gemini-3-flash',
        label: 'Gemini 3 Flash',
        description: 'Fast responses at scale',
      },
    ],
  },
]

export function AIModelTab() {
  const [selectedModel, setSelectedModel] = useState<SupportedModel | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function fetchSettings() {
      try {
        const settings = await getUserSettings()
        if (!cancelled) {
          setSelectedModel(settings.selected_model)
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load AI model settings.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchSettings()
    return () => {
      cancelled = true
    }
  }, [])

  const handleSelectModel = async (model: SupportedModel) => {
    if (model === selectedModel || saving) return

    setSaving(true)
    setError('')
    setSaveSuccess(false)

    const previous = selectedModel
    setSelectedModel(model)

    try {
      await updateUserSettings({ selected_model: model })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch {
      setSelectedModel(previous)
      setError('Failed to save model selection. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium text-[var(--text-primary)] mb-1">
          AI Model
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          Choose the AI model used for chat and expense processing
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" />
        </div>
      ) : (
        <div className="space-y-6">
          {MODEL_GROUPS.map((group) => (
            <div key={group.provider}>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2 px-1">
                {group.provider}
              </p>
              <div className="space-y-2">
                {group.models.map((model) => {
                  const isSelected = selectedModel === model.id
                  return (
                    <button
                      key={model.id}
                      onClick={() => handleSelectModel(model.id)}
                      disabled={saving}
                      aria-pressed={isSelected}
                      className={cn(
                        'w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left',
                        isSelected
                          ? 'bg-[var(--accent-muted)] border-[var(--accent-primary)]'
                          : 'bg-[var(--surface-secondary)] border-[var(--border-primary)] hover:bg-[var(--surface-hover)]',
                        saving && 'cursor-wait'
                      )}
                    >
                      {/* Radio indicator */}
                      <div
                        className={cn(
                          'w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors',
                          isSelected
                            ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]'
                            : 'border-[var(--border-primary)] bg-transparent'
                        )}
                      >
                        {isSelected && (
                          <div className="w-1.5 h-1.5 rounded-full bg-white" />
                        )}
                      </div>

                      {/* Label */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {model.label}
                        </p>
                        <p className="text-xs text-[var(--text-muted)]">
                          {model.description}
                        </p>
                      </div>

                      {/* Saved checkmark */}
                      {isSelected && saveSuccess && (
                        <Check className="h-4 w-4 text-[var(--accent-primary)] shrink-0" />
                      )}
                      {isSelected && saving && (
                        <Loader2 className="h-4 w-4 text-[var(--accent-primary)] shrink-0 animate-spin" />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-500">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
