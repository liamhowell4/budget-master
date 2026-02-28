import AVFoundation
import SwiftUI
import BudgetMaster

// MARK: - Recording State

enum WatchRecordingState {
    case idle
    case recording
    case uploading
    case success(ExpenseProcessResponse)
    case error(String)
}

// MARK: - WatchVoiceRecorder

/// AVAudioRecorder wrapper for watchOS.
///
/// Key differences from the iOS VoiceRecorder:
/// - No preview/playback states — hold to record, release to upload immediately
/// - Uses `.record` audio session category (`.playAndRecord` crashes on watchOS)
/// - 16 kHz sample rate (sufficient for Whisper, conserves battery)
/// - 30 fps metering (vs 60 fps on iOS)
/// - Auto-stops at 60 seconds via a safety timer
@MainActor
class WatchVoiceRecorder: NSObject, ObservableObject {

    // MARK: Published State

    @Published var state: WatchRecordingState = .idle
    @Published var recordingDuration: TimeInterval = 0
    @Published var waveformSamples: [Float] = []

    // MARK: Private

    private var audioRecorder: AVAudioRecorder?
    private var recordingURL: URL?
    private var meteringTimer: Timer?
    private var safetyTimer: Timer?

    private static let meteringInterval: TimeInterval = 1.0 / 30.0
    private static let maxDuration: TimeInterval = 60.0

    // MARK: Formatted Duration

    var formattedDuration: String {
        let total = Int(recordingDuration)
        return String(format: "%d:%02d", total / 60, total % 60)
    }

    // MARK: Start Recording

    func startRecording() {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("watch_voice_\(UUID().uuidString).m4a")
        recordingURL = url
        waveformSamples = []
        recordingDuration = 0

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.medium.rawValue
        ]

        do {
            let session = AVAudioSession.sharedInstance()
            // Use .record — .playAndRecord is not available on watchOS
            try session.setCategory(.record, mode: .default)
            try session.setActive(true)

            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
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
                    let dB = recorder.averagePower(forChannel: 0)
                    let normalized = Float(max(0.0, (dB + 60.0) / 60.0))
                    self.waveformSamples.append(normalized)
                    self.recordingDuration += Self.meteringInterval
                }
            }

            safetyTimer = Timer.scheduledTimer(
                withTimeInterval: Self.maxDuration,
                repeats: false
            ) { [weak self] _ in
                Task { @MainActor [weak self] in self?.stopAndUpload() }
            }
        } catch {
            state = .error("Failed to start recording: \(error.localizedDescription)")
        }
    }

    // MARK: Stop & Upload

    /// Stops the recorder and immediately uploads the recorded audio.
    func stopAndUpload() {
        guard case .recording = state else { return }

        stopTimers()
        audioRecorder?.stop()
        audioRecorder = nil

        guard let url = recordingURL else {
            state = .error("No recording file found.")
            return
        }

        state = .uploading

        Task {
            defer {
                try? FileManager.default.removeItem(at: url)
                recordingURL = nil
            }
            do {
                let audioData = try Data(contentsOf: url)
                let response = try await WatchExpenseService.uploadAudio(audioData)
                state = .success(response)
            } catch {
                state = .error(error.localizedDescription)
            }
        }
    }

    // MARK: Cancel

    func cancelRecording() {
        stopTimers()
        audioRecorder?.stop()
        audioRecorder = nil
        if let url = recordingURL {
            try? FileManager.default.removeItem(at: url)
            recordingURL = nil
        }
        reset()
    }

    // MARK: Reset to Idle

    func reset() {
        waveformSamples = []
        recordingDuration = 0
        state = .idle
    }

    // MARK: Private Helpers

    private func stopTimers() {
        meteringTimer?.invalidate()
        meteringTimer = nil
        safetyTimer?.invalidate()
        safetyTimer = nil
    }
}
