import AVFoundation
import Combine
import Foundation
import BudgetMaster

// MARK: - WatchRealtimeService

/// WebSocket client that connects the Watch to the backend's /ws/realtime endpoint,
/// which relays to OpenAI Realtime API for conversational voice.
///
/// Message flow:
///   send(audioChunk:) → {"type":"audio_chunk","data":"<base64>"}
///   sendAudioDone()   → {"type":"audio_done"}
///   sendCancel()      → {"type":"cancel"}
///
///   Receives:
///     input_transcript       → updates recorder state (typing indicator)
///     response_text_delta    → accumulates streamed text
///     response_audio_delta   → accumulates PCM16 audio
///     response_done          → plays audio + transitions to .success or .queryResult
///     error                  → transitions to .error
@MainActor
final class WatchRealtimeService: NSObject, ObservableObject {

    // Swift 6: @MainActor classes need an explicit nonisolated objectWillChange
    // to satisfy ObservableObject's protocol requirement without isolation mismatch.
    nonisolated let objectWillChange = ObservableObjectPublisher()

    // MARK: - Weak reference back to recorder for state updates
    weak var recorder: WatchVoiceRecorder?

    // MARK: - Private
    private var task: URLSessionWebSocketTask?
    private var pingTimer: Timer?
    private var accumulatedAudioData = Data()
    private var accumulatedText = ""
    private var audioPlayer: AVAudioPlayer?

    // MARK: - Connect

    func connect(token: String, voiceEnabled: Bool = true) {
        guard task == nil else { return }

        Task {
            // Build wss URL from the same base URL used by APIClient
            let baseURL = await APIClient.shared.getBaseURL()
            var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
            components.scheme = baseURL.scheme == "https" ? "wss" : "ws"
            components.path = "/ws/realtime"
            components.queryItems = [
                URLQueryItem(name: "token", value: token),
                URLQueryItem(name: "mode", value: voiceEnabled ? "voice" : "text"),
            ]

            guard let wsURL = components.url else { return }

            let session = URLSession(configuration: .default)
            let wsTask = session.webSocketTask(with: wsURL)
            self.task = wsTask
            wsTask.resume()

            self.startReceiving()
            self.startPingTimer()
        }
    }

    func disconnect() {
        pingTimer?.invalidate()
        pingTimer = nil
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
    }

    // MARK: - Send

    func send(audioChunk data: Data) {
        let base64 = data.base64EncodedString()
        sendJSON(["type": "audio_chunk", "data": base64])
    }

    func sendAudioDone() {
        sendJSON(["type": "audio_done"])
    }

    func sendCancel() {
        sendJSON(["type": "cancel"])
    }

    // MARK: - Private: receive loop

    private func startReceiving() {
        task?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let message):
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    switch message {
                    case .string(let text):
                        self.handle(message: text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self.handle(message: text)
                        }
                    @unknown default:
                        break
                    }
                    // Re-arm receive loop
                    self.startReceiving()
                }
            case .failure:
                // Connection dropped — let state machine handle gracefully
                break
            }
        }
    }

    private func handle(message text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        switch type {

        case "input_transcript":
            // User's spoken words appeared — we could show a "listening..." overlay
            // but for now we just ignore; the recorder is already in .processingResponse
            break

        case "response_text_delta":
            let delta = json["text"] as? String ?? ""
            accumulatedText += delta
            recorder?.state = .receivingResponse(accumulatedText)

        case "response_audio_delta":
            let b64 = json["data"] as? String ?? ""
            if let decoded = Data(base64Encoded: b64) {
                accumulatedAudioData.append(decoded)
            }

        case "response_done":
            let finalText = accumulatedText
            var expenseResponse: ExpenseProcessResponse? = nil

            if let expenseSaved = json["expense_saved"] as? [String: Any],
               let jsonData = try? JSONSerialization.data(withJSONObject: expenseSaved) {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                expenseResponse = try? decoder.decode(ExpenseProcessResponse.self, from: jsonData)
            }

            let audioData = accumulatedAudioData
            accumulatedAudioData = Data()
            accumulatedText = ""

            if let response = expenseResponse {
                recorder?.state = .success(response)
            } else {
                recorder?.state = .queryResult(finalText)
            }

            if !audioData.isEmpty {
                playAudio(pcm16Data: audioData)
            }

        case "error":
            let msg = json["message"] as? String ?? "Unknown error"
            recorder?.state = .error(msg)

        default:
            break
        }
    }

    // MARK: - Audio Playback

    private func playAudio(pcm16Data: Data) {
        let sampleRate: UInt32 = 24000
        let channels: UInt16 = 1
        let wavData = buildWAVHeader(pcm16Data: pcm16Data, sampleRate: sampleRate, channels: channels) + pcm16Data

        do {
            // Switch from .record to .playback
            let session = AVAudioSession.sharedInstance()
            try session.setActive(false)
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            audioPlayer = try AVAudioPlayer(data: wavData)
            audioPlayer?.play()
        } catch {
            // Non-fatal: audio playback failure shouldn't crash the app
        }
    }

    /// Builds a standard 44-byte WAV file header for raw PCM16 data.
    private func buildWAVHeader(pcm16Data: Data, sampleRate: UInt32, channels: UInt16) -> Data {
        let byteRate: UInt32 = sampleRate * UInt32(channels) * 2
        let blockAlign: UInt16 = channels * 2
        let dataSize = UInt32(pcm16Data.count)
        let chunkSize = 36 + dataSize

        var header = Data()
        header.append(contentsOf: Array("RIFF".utf8))
        header.append(contentsOf: withUnsafeBytes(of: chunkSize.littleEndian) { Array($0) })
        header.append(contentsOf: Array("WAVE".utf8))
        header.append(contentsOf: Array("fmt ".utf8))
        header.append(contentsOf: withUnsafeBytes(of: UInt32(16).littleEndian) { Array($0) }) // Subchunk1Size
        header.append(contentsOf: withUnsafeBytes(of: UInt16(1).littleEndian) { Array($0) })  // PCM = 1
        header.append(contentsOf: withUnsafeBytes(of: channels.littleEndian) { Array($0) })
        header.append(contentsOf: withUnsafeBytes(of: sampleRate.littleEndian) { Array($0) })
        header.append(contentsOf: withUnsafeBytes(of: byteRate.littleEndian) { Array($0) })
        header.append(contentsOf: withUnsafeBytes(of: blockAlign.littleEndian) { Array($0) })
        header.append(contentsOf: withUnsafeBytes(of: UInt16(16).littleEndian) { Array($0) }) // BitsPerSample
        header.append(contentsOf: Array("data".utf8))
        header.append(contentsOf: withUnsafeBytes(of: dataSize.littleEndian) { Array($0) })
        return header
    }

    // MARK: - Keepalive ping

    private func startPingTimer() {
        pingTimer = Timer.scheduledTimer(withTimeInterval: 20, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.task?.sendPing { _ in }
            }
        }
    }

    // MARK: - Private send helper

    private func sendJSON(_ dict: [String: String]) {
        guard let data = try? JSONSerialization.data(withJSONObject: dict),
              let text = String(data: data, encoding: .utf8) else { return }
        task?.send(.string(text)) { _ in }
    }
}
