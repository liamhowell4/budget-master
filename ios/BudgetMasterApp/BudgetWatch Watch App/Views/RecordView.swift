import SwiftUI
import WatchKit
import BudgetMaster

/// The main Watch screen.
///
/// States:
/// - **idle**      — Budget ring + hold-to-record button + "Expenses" link
/// - **recording** — Timer + waveform + red button + Cancel
/// - **uploading** — ProgressView + "Processing…"
/// - **success**   — Navigates to ConfirmationView (auto-returns after 3 s)
/// - **error**     — Error message + Retry button
struct RecordView: View {

    @StateObject private var recorder = WatchVoiceRecorder()
    @StateObject private var realtimeService = WatchRealtimeService()
    @State private var budgetStatus: BudgetStatus?
    @State private var showExpenses = false
    @State private var showConfirmation = false
    @State private var successResponse: ExpenseProcessResponse?
    @State private var isHolding = false
    @AppStorage("watchVoiceEnabled") private var voiceEnabled: Bool = true

    var body: some View {
        ZStack {
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
                    refreshBudget()
                }
            }
        }
        .sheet(isPresented: $showExpenses) {
            NavigationStack {
                ExpensesGlanceView()
            }
        }
        .task {
            refreshBudget()
            // Wire recorder to service before connecting
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

    // MARK: - Idle View

    private var idleView: some View {
        VStack(spacing: 8) {
            // Budget ring
            Group {
                if let budget = budgetStatus {
                    BudgetRingView(percentage: budget.totalPercentage / 100)
                } else {
                    ProgressView()
                }
            }
            .frame(width: 44, height: 44)

            // Hold-to-record button
            holdButton(isRecording: false)

            // Expenses glance link + voice/text mode toggle
            HStack(spacing: 16) {
                Button { showExpenses = true } label: {
                    Label("Expenses", systemImage: "list.bullet")
                        .font(.caption2)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)

                Button { voiceEnabled.toggle() } label: {
                    Image(systemName: voiceEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill")
                        .font(.caption2)
                        .foregroundStyle(voiceEnabled ? .blue : .secondary)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(voiceEnabled ? "Voice responses on" : "Voice responses off")
                .accessibilityHint("Toggles whether the assistant speaks its responses aloud")
            }
        }
    }

    // MARK: - Recording View

    private var recordingView: some View {
        VStack(spacing: 6) {
            Text(recorder.formattedDuration)
                .font(.title3.monospacedDigit())
                .foregroundStyle(.red)

            WatchWaveformView(samples: recorder.waveformSamples)
                .frame(height: 36)

            // Red hold button — release triggers upload
            holdButton(isRecording: true)

            Button("Cancel") {
                WKInterfaceDevice.current().play(.failure)
                recorder.cancelRecording()
            }
            .font(.caption2)
            .foregroundStyle(.secondary)
        }
    }

    // MARK: - Uploading View

    private var uploadingView: some View {
        VStack(spacing: 8) {
            ProgressView()
            Text("Processing…")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Processing View

    private var processingView: some View {
        VStack(spacing: 8) {
            ProgressView()
            Text("Thinking...")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Receiving Response View

    private func receivingView(_ text: String) -> some View {
        ScrollView {
            Text(text.isEmpty ? "..." : text)
                .font(.caption2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 4)
        }
    }

    // MARK: - Query Result View

    private func queryResultView(_ text: String) -> some View {
        VStack(spacing: 8) {
            ScrollView {
                Text(text)
                    .font(.caption2)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 4)
            }
            Button("Done") {
                recorder.reset()
            }
            .font(.caption)
        }
        .task {
            // Auto-dismiss after 8 seconds
            try? await Task.sleep(for: .seconds(8))
            if case .queryResult = recorder.state {
                recorder.reset()
            }
        }
    }

    // MARK: - Error View

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

    // MARK: - Hold-to-Record Button

    private func holdButton(isRecording: Bool) -> some View {
        ZStack {
            Circle()
                .fill(isRecording ? Color.red : Color.blue)
                .frame(width: 56, height: 56)
            Image(systemName: isRecording ? "waveform" : "mic.fill")
                .font(.title3)
                .foregroundStyle(.white)
        }
        .scaleEffect(isHolding ? 1.1 : 1.0)
        .animation(.spring(response: 0.2), value: isHolding)
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in
                    guard !isHolding else { return }
                    isHolding = true
                    WKInterfaceDevice.current().play(.start)
                    if !isRecording {
                        recorder.startRecording()
                    }
                }
                .onEnded { _ in
                    isHolding = false
                    if case .recording = recorder.state {
                        recorder.stopStreaming()
                    }
                }
        )
    }

    // MARK: - Helpers

    /// Disconnects any existing WebSocket session and opens a fresh one,
    /// passing the current voiceEnabled preference as the `mode` query param.
    private func connectRealtime() async {
        realtimeService.disconnect()
        if let token = try? await WatchTokenProvider.shared.getToken() {
            realtimeService.connect(token: token, voiceEnabled: voiceEnabled)
        }
    }

    private func refreshBudget() {
        Task { budgetStatus = try? await WatchExpenseService.fetchBudget() }
    }
}
