import SwiftUI
import WatchKit
import BudgetMaster

/// Center page of the three-page tab layout.
///
/// States:
/// - **idle**              — Large teal mic circle, hold-to-record, voice toggle at bottom.
/// - **recording**         — Red pulsing circle driven by microphone amplitude + timer.
/// - **processingResponse**— Spinner while the backend thinks.
/// - **receivingResponse** — Streaming text display as the model responds.
/// - **queryResult**       — Full analytics answer with auto-dismiss.
/// - **success**           — Navigates to ConfirmationView.
/// - **error**             — Yellow warning icon + message + retry.
struct RecordView: View {

    @StateObject private var recorder = WatchVoiceRecorder()
    @StateObject private var realtimeService = WatchRealtimeService()
    @State private var showConfirmation = false
    @State private var successResponse: ExpenseProcessResponse?
    @State private var isHolding = false
    @AppStorage("watchVoiceEnabled") private var voiceEnabled: Bool = true

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch recorder.state {
            case .idle:
                idleView
            case .recording:
                recordingView
            case .processingResponse:
                processingView
            case .receivingResponse(let text):
                receivingView(text)
            case .queryResult(let text):
                queryResultView(text)
            case .success(let response):
                Color.clear.onAppear {
                    successResponse = response
                    showConfirmation = true
                }
            case .error(let message):
                errorView(message)
            }
        }
        .navigationDestination(isPresented: $showConfirmation) {
            if let response = successResponse {
                ConfirmationView(response: response) {
                    showConfirmation = false
                    successResponse = nil
                    recorder.reset()
                }
            }
        }
        .task {
            // Wire recorder to service before connecting.
            realtimeService.recorder = recorder
            recorder.realtimeService = realtimeService
            await connectRealtime()
        }
        .onChange(of: voiceEnabled) { _, _ in
            Task { await connectRealtime() }
        }
        .onDisappear {
            realtimeService.disconnect()
        }
    }

    // MARK: - Idle

    private var idleView: some View {
        VStack(spacing: 0) {
            Spacer()

            // Layered glow rings + mic circle
            ZStack {
                // Outermost soft halo — expands on press for tactile feedback
                Circle()
                    .fill(Color.teal.opacity(0.12))
                    .frame(width: 92, height: 92)
                    .scaleEffect(isHolding ? 1.35 : 1.0)
                    .animation(.easeOut(duration: 0.2), value: isHolding)

                // Mid glow ring
                Circle()
                    .fill(Color.teal.opacity(0.22))
                    .frame(width: 74, height: 74)

                // Solid teal button
                Circle()
                    .fill(Color.teal)
                    .frame(width: 58, height: 58)

                Image(systemName: "mic.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
            }
            .scaleEffect(isHolding ? 1.08 : 1.0)
            .animation(.spring(response: 0.2, dampingFraction: 0.6), value: isHolding)
            .gesture(holdGesture(isRecording: false))
            .accessibilityLabel("Record expense")
            .accessibilityHint("Hold to record a voice expense")

            Spacer().frame(height: 10)

            Text("Hold to record")
                .font(.caption2)
                .foregroundStyle(.secondary)

            Spacer()

            // Voice output toggle
            Button {
                voiceEnabled.toggle()
            } label: {
                Label(
                    voiceEnabled ? "Voice on" : "Voice off",
                    systemImage: voiceEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill"
                )
                .font(.system(size: 11))
                .foregroundStyle(voiceEnabled ? .teal : .secondary)
            }
            .buttonStyle(.plain)
            .padding(.bottom, 6)
            .accessibilityLabel(voiceEnabled ? "Voice responses on" : "Voice responses off")
            .accessibilityHint("Toggles whether the assistant speaks its responses aloud")
        }
    }

    // MARK: - Recording

    private var recordingView: some View {
        VStack(spacing: 8) {
            ZStack {
                // Amplitude-driven outer pulse ring
                Circle()
                    .fill(Color.red.opacity(0.15))
                    .frame(width: 92, height: 92)
                    .scaleEffect(amplitudeScale)
                    .animation(.easeInOut(duration: 0.1), value: amplitudeScale)

                // Solid red button
                Circle()
                    .fill(Color.red)
                    .frame(width: 58, height: 58)

                Image(systemName: "waveform")
                    .font(.title2)
                    .foregroundStyle(.white)
            }
            .gesture(holdGesture(isRecording: true))
            .accessibilityLabel("Recording in progress")
            .accessibilityHint("Release to send")

            Text(recorder.formattedDuration)
                .font(.body.monospacedDigit())
                .foregroundStyle(.red)

            Button("Cancel") {
                WKInterfaceDevice.current().play(.failure)
                recorder.cancelRecording()
            }
            .font(.caption2)
            .foregroundStyle(.secondary)
            .buttonStyle(.plain)
        }
    }

    // MARK: - Processing

    private var processingView: some View {
        VStack(spacing: 8) {
            ProgressView()
                .tint(.teal)
            Text("Thinking\u{2026}")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Receiving

    private func receivingView(_ text: String) -> some View {
        ScrollView {
            Text(text.isEmpty ? "\u{2026}" : text)
                .font(.caption2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 4)
        }
    }

    // MARK: - Query Result

    private func queryResultView(_ text: String) -> some View {
        VStack(spacing: 8) {
            ScrollView {
                Text(text)
                    .font(.caption2)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 4)
            }
            Button("Done") { recorder.reset() }
                .font(.caption)
        }
        .task {
            // Auto-dismiss after 8 seconds of inactivity.
            try? await Task.sleep(for: .seconds(8))
            if case .queryResult = recorder.state { recorder.reset() }
        }
    }

    // MARK: - Error

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.title2)
                .foregroundStyle(.yellow)
            Text(message)
                .font(.caption2)
                .multilineTextAlignment(.center)
                .lineLimit(3)
            Button("Retry") { recorder.reset() }
                .font(.caption)
        }
        .onAppear { WKInterfaceDevice.current().play(.failure) }
    }

    // MARK: - Hold Gesture

    /// A zero-minimum-distance drag gesture that starts recording on finger-down
    /// and stops streaming on finger-up. Works for both idle and recording states.
    private func holdGesture(isRecording: Bool) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { _ in
                guard !isHolding else { return }
                isHolding = true
                WKInterfaceDevice.current().play(.start)
                if !isRecording { recorder.startRecording() }
            }
            .onEnded { _ in
                isHolding = false
                if case .recording = recorder.state { recorder.stopStreaming() }
            }
    }

    // MARK: - Helpers

    /// Maps the latest waveform sample (0–1) to a scale multiplier for the pulse ring.
    private var amplitudeScale: CGFloat {
        1.0 + CGFloat(recorder.waveformSamples.last ?? 0) * 0.5
    }

    /// Disconnects any existing WebSocket session and opens a fresh one,
    /// passing the current voiceEnabled preference as the mode query param.
    private func connectRealtime() async {
        realtimeService.disconnect()
        if let token = try? await WatchTokenProvider.shared.getToken() {
            realtimeService.connect(token: token, voiceEnabled: voiceEnabled)
        }
    }
}
