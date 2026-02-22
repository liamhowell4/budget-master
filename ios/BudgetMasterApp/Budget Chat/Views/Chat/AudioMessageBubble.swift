import AVFoundation
import SwiftUI

// MARK: - AudioBubblePlayer

/// A lightweight AVAudioPlayer wrapper scoped to a single bubble.
/// Conforms to NSObject so it can serve as AVAudioPlayerDelegate.
@MainActor
final class AudioBubblePlayer: NSObject, ObservableObject, AVAudioPlayerDelegate {

    @Published var isPlaying = false
    @Published var progress: Double = 0

    var duration: TimeInterval {
        player?.duration ?? 0
    }

    private var player: AVAudioPlayer?
    private var timer: Timer?

    // ~30 fps is more than enough for smooth progress updates
    private static let timerInterval: TimeInterval = 1.0 / 30.0

    // MARK: Playback Control

    func play(url: URL) {
        if player == nil {
            do {
                let session = AVAudioSession.sharedInstance()
                try session.setCategory(.playback, mode: .default)
                try session.setActive(true)
                player = try AVAudioPlayer(contentsOf: url)
                player?.delegate = self
            } catch {
                return
            }
        }
        player?.play()
        isPlaying = true
        startProgressTimer()
    }

    func pause() {
        player?.pause()
        isPlaying = false
        stopProgressTimer()
    }

    func togglePlayback(url: URL?) {
        if isPlaying {
            pause()
        } else {
            guard let url else { return }
            play(url: url)
        }
    }

    // MARK: AVAudioPlayerDelegate

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.isPlaying = false
            self.progress = 0
            self.stopProgressTimer()
            // Reset player so next tap starts from beginning
            self.player = nil
        }
    }

    // MARK: Private

    private func startProgressTimer() {
        stopProgressTimer()
        timer = Timer.scheduledTimer(withTimeInterval: Self.timerInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self, let p = self.player, p.duration > 0 else { return }
                self.progress = p.currentTime / p.duration
            }
        }
    }

    private func stopProgressTimer() {
        timer?.invalidate()
        timer = nil
    }
}

// MARK: - AudioMessageBubble

/// A chat bubble that renders a voice memo with play/pause, a waveform,
/// and a duration label — styled to match the existing MessageBubble.
struct AudioMessageBubble: View {
    let message: ChatMessage

    @StateObject private var player = AudioBubblePlayer()
    @Environment(\.appUserBubble) private var userBubble
    @Environment(\.appUserBubbleText) private var userBubbleText

    var body: some View {
        HStack {
            if message.isUser { Spacer(minLength: 60) }

            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                // Main bubble
                HStack(spacing: 10) {
                    // Play / pause button
                    Button {
                        player.togglePlayback(url: message.audioMetadata?.localFileURL)
                    } label: {
                        Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(userBubbleText)
                            .frame(width: 28, height: 28)
                            .background(userBubbleText.opacity(0.2))
                            .clipShape(Circle())
                    }
                    .accessibilityLabel(player.isPlaying ? "Pause voice memo" : "Play voice memo")

                    // Waveform
                    WaveformView(
                        samples: message.audioMetadata?.waveformSamples ?? [],
                        progress: player.isPlaying ? player.progress : (player.progress > 0 ? player.progress : 1.0),
                        activeColor: userBubbleText,
                        inactiveColor: userBubbleText.opacity(0.35)
                    )
                    .frame(height: 28)
                    .frame(minWidth: 80)

                    // Duration label
                    Text(durationText)
                        .font(.caption2)
                        .fontWeight(.medium)
                        .foregroundStyle(userBubbleText.opacity(0.8))
                        .monospacedDigit()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(userBubble)
                .cornerRadius(16)

                // Timestamp — same as MessageBubble
                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            if !message.isUser { Spacer(minLength: 60) }
        }
        .padding(.horizontal)
    }

    // MARK: Private

    private var durationText: String {
        if let meta = message.audioMetadata {
            // Show current playback position while playing, total duration otherwise
            let displayDuration = player.progress > 0 && player.isPlaying
                ? player.progress * meta.duration
                : meta.duration
            return formatDuration(displayDuration)
        }
        return "0:00"
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    let fakeSamples: [Float] = (0..<60).map { i in
        Float.random(in: 0.05...1.0) * abs(sin(Float(i) * 0.25))
    }
    let meta = AudioMetadata(duration: 7.5, waveformSamples: fakeSamples, localFileURL: nil)
    let msg = ChatMessage(content: "", isUser: true, audioMetadata: meta)

    return VStack(spacing: 12) {
        AudioMessageBubble(message: msg)
    }
    .padding()
}
#endif
