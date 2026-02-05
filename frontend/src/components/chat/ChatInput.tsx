import { cn } from '@/utils/cn'
import { useState, useRef, useEffect } from 'react'
import { ArrowUp } from 'lucide-react'
import { VoiceRecordButton } from './VoiceRecordButton'
import { useVoiceRecording } from '@/hooks/useVoiceRecording'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  onSendAudio: (audio: Blob) => void
  disabled?: boolean
}

export function ChatInput({ onSendMessage, onSendAudio, disabled }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { isRecording, startRecording, stopRecording } = useVoiceRecording({
    onRecordingComplete: onSendAudio,
  })

  // Kill the outline directly on the DOM element with !important
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.setProperty('outline', 'none', 'important')
      textareaRef.current.style.setProperty('outline-width', '0', 'important')
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleFocus = () => {
    setIsFocused(true)
    // Force remove outline on focus with !important
    if (textareaRef.current) {
      textareaRef.current.style.setProperty('outline', 'none', 'important')
      textareaRef.current.style.setProperty('outline-width', '0', 'important')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative rounded-lg">
      {/* Apple Intelligence glow effect - visible when focused */}
      {isFocused && <div className="apple-intelligence-glow rounded-lg" />}

      <div
        className={cn(
          'relative flex items-end gap-2 rounded-lg',
          'bg-[var(--surface-secondary)]',
          'border border-[var(--border-primary)]',
          'transition-colors',
          'p-2'
        )}
      >
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={() => setIsFocused(false)}
          placeholder="Track an expense..."
          disabled={disabled || isRecording}
          rows={1}
          className={cn(
            'flex-1 bg-transparent px-2 py-1.5 resize-none',
            'text-sm text-[var(--text-primary)]',
            'placeholder:text-[var(--text-muted)]',
            'disabled:opacity-50',
            'max-h-32'
          )}
          style={{ minHeight: '36px', outline: 'none' }}
        />

        <div className="flex items-center gap-1">
          <VoiceRecordButton
            isRecording={isRecording}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            disabled={disabled || !!message.trim()}
          />

          <button
            type="submit"
            disabled={disabled || !message.trim() || isRecording}
            className={cn(
              'flex items-center justify-center',
              'h-8 w-8 rounded-md transition-colors',
              message.trim() && !disabled
                ? 'bg-[var(--text-primary)] text-[var(--text-inverted)]'
                : 'bg-[var(--surface-secondary)] text-[var(--text-muted)] cursor-not-allowed'
            )}
            aria-label="Send message"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
      </div>
    </form>
  )
}
