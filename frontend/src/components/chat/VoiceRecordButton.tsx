import { cn } from '@/utils/cn'
import { Mic, Square } from 'lucide-react'

interface VoiceRecordButtonProps {
  isRecording: boolean
  onStartRecording: () => void
  onStopRecording: () => void
  disabled?: boolean
}

export function VoiceRecordButton({
  isRecording,
  onStartRecording,
  onStopRecording,
  disabled,
}: VoiceRecordButtonProps) {
  return (
    <button
      type="button"
      onClick={isRecording ? onStopRecording : onStartRecording}
      disabled={disabled}
      className={cn(
        'flex items-center justify-center',
        'h-8 w-8 rounded-md transition-colors',
        isRecording
          ? 'bg-red-500 text-white'
          : 'text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      aria-label={isRecording ? 'Stop recording' : 'Start recording'}
    >
      {isRecording ? (
        <Square className="h-3.5 w-3.5" fill="currentColor" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </button>
  )
}
