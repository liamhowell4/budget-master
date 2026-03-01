import SwiftUI
import WatchKit
import BudgetMaster

/// Center page of the three-page tab layout.
///
/// States:
/// - **idle**               — Teal mic circle; tap to open system dictation.
/// - **processingResponse** — Spinner while the backend processes the dictated text.
/// - **queryResult**        — Analytics answer with auto-dismiss after 8 seconds.
/// - **success**            — Navigates to ConfirmationView with expense details.
/// - **error**              — Yellow warning icon + message + retry.
struct RecordView: View {

    @StateObject private var recorder = WatchVoiceRecorder()
    @State private var showConfirmation = false
    @State private var successResponse: ExpenseProcessResponse?
    @State private var showInput = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch recorder.state {
            case .idle:
                idleView
            case .processingResponse:
                processingView
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
        .sheet(isPresented: $showInput) {
            DictationInputView { text in
                showInput = false
                recorder.submitText(text)
            }
        }
    }

    // MARK: - Idle

    private var idleView: some View {
        VStack(spacing: 0) {
            Spacer()

            ZStack {
                Circle()
                    .fill(Color.teal.opacity(0.12))
                    .frame(width: 92, height: 92)

                Circle()
                    .fill(Color.teal.opacity(0.22))
                    .frame(width: 74, height: 74)

                Circle()
                    .fill(Color.teal)
                    .frame(width: 58, height: 58)

                Image(systemName: "mic.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
            }
            .onTapGesture {
                startDictation()
            }
            .accessibilityLabel("Record expense")
            .accessibilityHint("Tap to dictate a voice expense")

            Spacer().frame(height: 10)

            Text("Tap to record")
                .font(.caption2)
                .foregroundStyle(.secondary)

            Spacer()
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

    // MARK: - Dictation

    private func startDictation() {
        WKInterfaceDevice.current().play(.click)
        showInput = true
    }
}

// MARK: - DictationInputView

/// A thin sheet that focuses a TextField immediately on appear,
/// triggering watchOS's system dictation / input controller.
/// When the user confirms their text, onSubmit is called.
private struct DictationInputView: View {
    let onSubmit: (String) -> Void

    @State private var text = ""
    @FocusState private var focused: Bool
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 10) {
            TextField("Expense\u{2026}", text: $text)
                .focused($focused)
                .onSubmit { submit() }

            Button("Submit") { submit() }
                .font(.caption)
                .disabled(text.trimmingCharacters(in: .whitespaces).isEmpty)
        }
        .padding(.horizontal, 4)
        .onAppear { focused = true }
    }

    private func submit() {
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }
        onSubmit(trimmed)
    }
}
