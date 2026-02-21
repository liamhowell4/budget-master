import AVFoundation
import SwiftUI

@MainActor
class VoiceRecorder: ObservableObject {
    @Published var isRecording = false
    @Published var recordingDuration: TimeInterval = 0
    @Published var permissionDenied = false

    private var audioRecorder: AVAudioRecorder?
    private var recordingURL: URL?
    private var timer: Timer?

    var formattedDuration: String {
        let mins = Int(recordingDuration) / 60
        let secs = Int(recordingDuration) % 60
        return String(format: "%d:%02d", mins, secs)
    }

    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        switch session.recordPermission {
        case .undetermined:
            session.requestRecordPermission { [weak self] allowed in
                Task { @MainActor in
                    if allowed {
                        self?.beginRecording()
                    } else {
                        self?.permissionDenied = true
                    }
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

    func stopRecording() -> URL? {
        timer?.invalidate()
        timer = nil
        audioRecorder?.stop()
        isRecording = false
        let url = recordingURL
        audioRecorder = nil
        return url
    }

    func cancelRecording() {
        timer?.invalidate()
        timer = nil
        audioRecorder?.stop()
        if let url = recordingURL { try? FileManager.default.removeItem(at: url) }
        audioRecorder = nil
        recordingURL = nil
        isRecording = false
        recordingDuration = 0
    }

    private func beginRecording() {
        let tempDir = FileManager.default.temporaryDirectory
        let fileName = "voice_\(UUID().uuidString).m4a"
        let url = tempDir.appendingPathComponent(fileName)
        recordingURL = url

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
            audioRecorder?.record()
            isRecording = true
            recordingDuration = 0

            timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
                Task { @MainActor [weak self] in
                    self?.recordingDuration += 1
                }
            }
        } catch {
            isRecording = false
        }
    }
}
