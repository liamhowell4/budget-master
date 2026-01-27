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
          'bg-neutral-50 dark:bg-neutral-900',
          'border border-neutral-200 dark:border-neutral-800',
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
            'text-base text-neutral-900 dark:text-neutral-100', // 16px prevents iOS auto-zoom
            'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
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
                ? 'bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900'
                : 'bg-neutral-200 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500 cursor-not-allowed'
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
