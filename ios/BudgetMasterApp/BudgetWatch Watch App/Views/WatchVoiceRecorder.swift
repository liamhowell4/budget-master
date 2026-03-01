import Combine
import SwiftUI
import BudgetMaster

// MARK: - Recording State

enum WatchRecordingState {
    case idle
    case processingResponse
    case queryResult(String)
    case success(ExpenseProcessResponse)
    case error(String)
}

// MARK: - WatchVoiceRecorder

/// Lightweight state machine for the Watch dictation flow.
///
/// Voice capture is delegated to the system via WKExtension.presentTextInputController.
/// This class receives the transcribed text and manages the backend request lifecycle.
@MainActor
class WatchVoiceRecorder: ObservableObject {

    @Published var state: WatchRecordingState = .idle

    // MARK: Submit

    func submitText(_ text: String) {
        state = .processingResponse
        Task {
            do {
                let response = try await WatchExpenseService.submitText(text)
                if response.expenseId != nil {
                    state = .success(response)
                } else {
                    state = .queryResult(response.message)
                }
            } catch {
                state = .error(error.localizedDescription)
            }
        }
    }

    // MARK: Reset

    func reset() {
        state = .idle
    }
}
