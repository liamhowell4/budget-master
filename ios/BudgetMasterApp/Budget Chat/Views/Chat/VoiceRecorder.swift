import AVFoundation
import AVFAudio
import SwiftUI

// MARK: - Recording State

enum RecordingState {
    case idle
    case recording
    case preview
}

// MARK: - VoiceRecorder

@MainActor
class VoiceRecorder: NSObject, ObservableObject, AVAudioPlayerDelegate {

    // MARK: Published State

    @Published var state: RecordingState = .idle
    @Published var recordingDuration: TimeInterval = 0
    @Published var permissionDenied = false
    @Published var waveformSamples: [Float] = []
    @Published var isPlaying = false
    @Published var playbackProgress: Double = 0

    // Backward-compat shim for any existing callers that read isRecording directly
    var isRecording: Bool { state == .recording }

    // MARK: Private

    private var audioRecorder: AVAudioRecorder?
    private var audioPlayer: AVAudioPlayer?
    private var recordingURL: URL?
    private var meteringTimer: Timer?
    private var playbackTimer: Timer?

    // ~60 fps metering keeps the waveform smooth during recording
    private static let meteringInterval: TimeInterval = 1.0 / 60.0
    // ~30 fps is sufficient for playback progress updates
    private static let playbackInterval: TimeInterval = 1.0 / 30.0

    // MARK: Formatted Duration

    var formattedDuration: String {
        formatDuration(recordingDuration)
    }

    // MARK: Permission / Start

    func startRecording() {
        switch AVAudioApplication.shared.recordPermission {
        case .undetermined:
            AVAudioApplication.requestRecordPermission { [weak self] allowed in
                Task { @MainActor [weak self] in
                    if allowed { self?.beginRecording() }
                    else { self?.permissionDenied = true }
                }
            }
        case .denied:
            permissionDenied = true
        case .granted:
            beginRecording()
        @unknown default:
            permissionDenied = true
        }
    }

    // MARK: Stop → Preview

    /// Stops the recorder and transitions to .preview state.
    /// The URL is retained internally; call finishAndGetURL() to extract it on send.
    func stopRecording() {
        meteringTimer?.invalidate()
        meteringTimer = nil
        audioRecorder?.stop()
        // Keep audioRecorder reference alive so the file stays accessible
        state = .preview
    }

    /// Returns the recorded file URL and resets back to idle.
    /// Call this when the user confirms they want to send the voice memo.
    func finishAndGetURL() -> URL? {
        let url = recordingURL
        resetToIdle()
        return url
    }

    // MARK: Cancel

    func cancelRecording() {
        // Stop playback if in progress
        if isPlaying {
            audioPlayer?.stop()
            isPlaying = false
        }
        playbackTimer?.invalidate()
        playbackTimer = nil

        // Stop any ongoing recording
        meteringTimer?.invalidate()
        meteringTimer = nil
        audioRecorder?.stop()
        audioRecorder = nil

        // Delete temp file
        if let url = recordingURL {
            try? FileManager.default.removeItem(at: url)
        }

        resetToIdle()
    }

    // MARK: Preview Playback

    func playPreview() {
        guard state == .preview, let url = recordingURL else { return }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.delegate = self
            audioPlayer?.play()
            isPlaying = true

            playbackTimer?.invalidate()
            playbackTimer = Timer.scheduledTimer(
                withTimeInterval: Self.playbackInterval,
                repeats: true
            ) { [weak self] _ in
                Task { @MainActor [weak self] in
                    guard let self, let player = self.audioPlayer, player.duration > 0 else { return }
                    self.playbackProgress = player.currentTime / player.duration
                }
            }
        } catch {
            isPlaying = false
        }
    }

    func pausePreview() {
        audioPlayer?.pause()
        isPlaying = false
        playbackTimer?.invalidate()
        playbackTimer = nil
    }

    /// Alias for cancelRecording — deletes the preview and returns to idle.
    func deletePreview() {
        cancelRecording()
    }

    // MARK: AVAudioPlayerDelegate

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.isPlaying = false
            self.playbackProgress = 1.0
            self.playbackTimer?.invalidate()
            self.playbackTimer = nil
        }
    }

    // MARK: Private Helpers

    private func beginRecording() {
        let tempDir = FileManager.default.temporaryDirectory
        let fileName = "voice_\(UUID().uuidString).m4a"
        let url = tempDir.appendingPathComponent(fileName)
        recordingURL = url
        waveformSamples = []
        recordingDuration = 0

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker])
            try session.setActive(true)

            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            // Enable metering so we can sample amplitude for the live waveform
            audioRecorder?.isMeteringEnabled = true
            audioRecorder?.record()
            state = .recording

            meteringTimer = Timer.scheduledTimer(
                withTimeInterval: Self.meteringInterval,
                repeats: true
            ) { [weak self] _ in
                Task { @MainActor [weak self] in
                    guard let self, let recorder = self.audioRecorder else { return }
                    recorder.updateMeters()
                    // averagePower returns dB in [-160, 0]; clamp to [-60, 0] for meaningful display
                    let dB = recorder.averagePower(forChannel: 0)
                    let normalized = Float(max(0.0, (dB + 60.0) / 60.0))
                    self.waveformSamples.append(normalized)
                    self.recordingDuration += Self.meteringInterval
                }
            }
        } catch {
            state = .idle
        }
    }

    private func resetToIdle() {
        audioRecorder = nil
        audioPlayer = nil
        recordingURL = nil
        recordingDuration = 0
        waveformSamples = []
        isPlaying = false
        playbackProgress = 0
        state = .idle
    }
}

// MARK: - Duration Formatter (module-level utility)

func formatDuration(_ duration: TimeInterval) -> String {
    let total = Int(duration)
    let mins = total / 60
    let secs = total % 60
    return String(format: "%d:%02d", mins, secs)
}
