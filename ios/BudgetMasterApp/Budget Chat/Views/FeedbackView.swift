import SwiftUI

// MARK: - Feedback Type

private enum FeedbackType: String, CaseIterable, Identifiable {
    case bug = "bug"
    case feature = "feature"
    case general = "general"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .bug:     return "Bug"
        case .feature: return "Feature Request"
        case .general: return "General"
        }
    }

    var icon: String {
        switch self {
        case .bug:     return "ant.fill"
        case .feature: return "lightbulb.fill"
        case .general: return "bubble.left.fill"
        }
    }
}

// MARK: - Feedback View Model

@MainActor
private final class FeedbackViewModel: ObservableObject {
    @Published var selectedType: FeedbackType = .general
    @Published var message: String = ""
    @Published var isSubmitting: Bool = false
    @Published var submissionError: String?
    @Published var didSucceed: Bool = false

    private let api = APIService()

    /// True once the user has typed at least one non-whitespace character.
    var canSubmit: Bool {
        !message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func submit(userEmail: String) async {
        guard canSubmit else { return }
        isSubmitting = true
        submissionError = nil

        do {
            try await api.submitFeedback(
                type: selectedType.rawValue,
                message: message.trimmingCharacters(in: .whitespacesAndNewlines),
                userEmail: userEmail
            )
            withAnimation(.spring(response: 0.4, dampingFraction: 0.75)) {
                didSucceed = true
            }
        } catch {
            submissionError = error.localizedDescription
        }

        isSubmitting = false
    }

    func reset() {
        withAnimation(.spring(response: 0.4, dampingFraction: 0.75)) {
            didSucceed = false
            message = ""
            selectedType = .general
            submissionError = nil
        }
    }
}

// MARK: - Feedback View

struct FeedbackView: View {
    @EnvironmentObject private var authManager: AuthenticationManager
    @Environment(\.appAccent) private var appAccent

    @StateObject private var viewModel = FeedbackViewModel()
    @FocusState private var isEditorFocused: Bool

    private var userEmail: String {
        authManager.currentUser?.email ?? ""
    }

    var body: some View {
        NavigationStack {
            ZStack {
                // Matching the pattern from other views: a ScrollView that dismisses
                // the keyboard when the user taps the background.
                ScrollView {
                    VStack(spacing: 24) {
                        if viewModel.didSucceed {
                            successView
                                .transition(.asymmetric(
                                    insertion: .scale(scale: 0.85).combined(with: .opacity),
                                    removal: .opacity
                                ))
                        } else {
                            formView
                                .transition(.asymmetric(
                                    insertion: .opacity,
                                    removal: .scale(scale: 0.9).combined(with: .opacity)
                                ))
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 8)
                    .padding(.bottom, 40)
                    .animation(.spring(response: 0.4, dampingFraction: 0.75), value: viewModel.didSucceed)
                }
                .scrollDismissesKeyboard(.interactively)
            }
            .navigationTitle("Feedback")
            .navigationBarTitleDisplayMode(.large)
        }
    }

    // MARK: - Form

    private var formView: some View {
        VStack(spacing: 24) {
            // Subtitle
            Text("Help us improve")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)

            // Type selector chips
            typePicker

            // Message editor
            messageEditor

            // Error banner (sits between editor and submit button)
            if let error = viewModel.submissionError {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.red)
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.leading)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .glassCard(cornerRadius: 12)
                .accessibilityLabel("Submission error: \(error)")
            }

            // Submit button
            submitButton
        }
    }

    // MARK: - Type Picker

    private var typePicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Type")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(.secondary)

            HStack(spacing: 10) {
                ForEach(FeedbackType.allCases) { type in
                    FeedbackChip(
                        type: type,
                        isSelected: viewModel.selectedType == type,
                        accentColor: appAccent
                    ) {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                            viewModel.selectedType = type
                        }
                    }
                }
            }
        }
    }

    // MARK: - Message Editor

    private var messageEditor: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Message")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(.secondary)

            ZStack(alignment: .topLeading) {
                // Placeholder — visible only when message is empty and editor is unfocused.
                if viewModel.message.isEmpty {
                    Text("Tell us what's on your mind...")
                        .font(.body)
                        .foregroundStyle(Color(uiColor: .placeholderText))
                        .padding(.top, 8)
                        .padding(.leading, 4)
                        .allowsHitTesting(false)
                }

                TextEditor(text: $viewModel.message)
                    .font(.body)
                    .focused($isEditorFocused)
                    .frame(minHeight: 140)
                    .scrollContentBackground(.hidden)
                    // Trim the default TextEditor inset so the placeholder aligns precisely.
                    .padding(.top, 0)
            }
            .padding(12)
            .glassCard(cornerRadius: 16)
            .onTapGesture {
                isEditorFocused = true
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Feedback message")
        .accessibilityHint("Enter your feedback here")
    }

    // MARK: - Submit Button

    private var submitButton: some View {
        Button {
            isEditorFocused = false
            Task { await viewModel.submit(userEmail: userEmail) }
        } label: {
            Group {
                if viewModel.isSubmitting {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(.white)
                } else {
                    Text("Submit Feedback")
                        .font(.body)
                        .fontWeight(.semibold)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 50)
            .foregroundStyle(.white)
            .background(viewModel.canSubmit ? appAccent : Color(uiColor: .systemGray3))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            // Animate the background color change when canSubmit flips.
            .animation(.easeInOut(duration: 0.2), value: viewModel.canSubmit)
        }
        .disabled(!viewModel.canSubmit || viewModel.isSubmitting)
        .accessibilityLabel("Submit feedback")
        .accessibilityHint("Sends your feedback to the development team")
    }

    // MARK: - Success State

    private var successView: some View {
        VStack(spacing: 28) {
            Spacer(minLength: 48)

            // Confirmation icon
            ZStack {
                Circle()
                    .fill(appAccent.opacity(0.15))
                    .frame(width: 96, height: 96)

                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 52))
                    .foregroundStyle(appAccent)
                    .symbolRenderingMode(.hierarchical)
            }

            VStack(spacing: 8) {
                Text("Thank you!")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Your feedback has been submitted.\nWe read every message.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }

            // Send more feedback
            Button {
                viewModel.reset()
            } label: {
                Text("Send More Feedback")
                    .font(.body)
                    .fontWeight(.semibold)
                    .foregroundStyle(appAccent)
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .overlay {
                        RoundedRectangle(cornerRadius: 14)
                            .strokeBorder(appAccent, lineWidth: 1.5)
                    }
            }
            .accessibilityLabel("Send more feedback")

            Spacer(minLength: 48)
        }
    }
}

// MARK: - Feedback Chip

/// A single type-selection chip button. Extracted to keep FeedbackView's body readable.
private struct FeedbackChip: View {
    let type: FeedbackType
    let isSelected: Bool
    let accentColor: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: type.icon)
                    .font(.caption)
                    .symbolRenderingMode(.hierarchical)
                Text(type.label)
                    .font(.caption)
                    .fontWeight(.medium)
                    .lineLimit(1)
            }
            .foregroundStyle(isSelected ? .white : .primary)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background {
                if isSelected {
                    Capsule().fill(accentColor)
                } else {
                    // Unselected chips use the glass capsule material.
                    Capsule().fill(Color(uiColor: .secondarySystemBackground))
                }
            }
            // Subtle border on unselected state for definition in light mode.
            .overlay {
                if !isSelected {
                    Capsule()
                        .strokeBorder(Color(uiColor: .separator), lineWidth: 0.5)
                }
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(type.label)
        .accessibilityAddTraits(isSelected ? [.isSelected] : [])
        .accessibilityHint("Select feedback type: \(type.label)")
    }
}

// MARK: - Preview

#Preview {
    FeedbackView()
        .environmentObject(AuthenticationManager())
}
