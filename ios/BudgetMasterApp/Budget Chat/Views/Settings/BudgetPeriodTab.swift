import SwiftUI
import BudgetMaster

struct BudgetPeriodTab: View {
    @StateObject private var viewModel = BudgetPeriodViewModel()
    @Environment(\.appAccent) private var appAccent

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Info callout
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: "info.circle.fill")
                        .foregroundStyle(appAccent)
                        .font(.body)
                    Text("Your budget runs monthly. Pick which day of the month it starts.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(12)
                .glassCard()

                if let error = viewModel.errorMessage {
                    errorBanner(error)
                }

                if viewModel.saveSuccess {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                        Text("Settings saved")
                            .font(.subheadline)
                            .foregroundStyle(.green)
                    }
                    .transition(.opacity)
                }

                // 3-way segment picker: First / Last / Specific
                MonthStartDayPicker(
                    selection: $viewModel.monthStartDay,
                    specificDay: $viewModel.specificDay
                )

                // Save button
                Button {
                    Task { await viewModel.save() }
                } label: {
                    HStack(spacing: 8) {
                        if viewModel.isSaving {
                            ProgressView()
                                .progressViewStyle(.circular)
                                .tint(.white)
                                .scaleEffect(0.8)
                        }
                        Text(viewModel.isSaving ? "Saving..." : "Save Changes")
                            .font(.body.weight(.semibold))
                    }
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(appAccent)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(viewModel.isSaving)
            }
            .padding()
        }
        .task {
            await viewModel.loadSettings()
        }
        .overlay {
            if viewModel.isLoading {
                ProgressView()
            }
        }
    }

    // MARK: - Error Banner

    private func errorBanner(_ message: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
            Button {
                Task { await viewModel.loadSettings() }
            } label: {
                Text("Retry")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(viewModel.errorMessage != nil ? Color.accentColor : .secondary)
            }
        }
        .padding(12)
        .glassCard()
    }
}

// MARK: - MonthStartDayPicker

/// Shared 3-segment picker used in both Settings and Onboarding.
/// `selection` is the live MonthStartDay binding; `specificDay` is a scratch
/// value that persists the user's last chosen day number so switching away from
/// "Specific" and back restores it.
struct MonthStartDayPicker: View {
    @Binding var selection: MonthStartDay
    /// Retained "specific" day value — persists across mode switches, 1...28.
    @Binding var specificDay: Int

    @Environment(\.appAccent) private var appAccent

    /// Which segment is currently highlighted.
    private enum Segment: Int, CaseIterable {
        case first, last, specific

        var label: String {
            switch self {
            case .first: return "First"
            case .last: return "Last"
            case .specific: return "Specific"
            }
        }
    }

    private var activeSegment: Segment {
        switch selection {
        case .day(1): return .first
        case .last:   return .last
        default:      return .specific
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Budget month starts on")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 4)

            // Segmented control
            Picker("Start Day Mode", selection: segmentBinding) {
                ForEach(Segment.allCases, id: \.self) { seg in
                    Text(seg.label).tag(seg)
                }
            }
            .pickerStyle(.segmented)

            // Specific day sub-picker — only visible when Specific is selected
            if activeSegment == .specific {
                HStack(spacing: 12) {
                    Text("Day:")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    TextField("", value: $specificDay, format: .number)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 60)
                        .multilineTextAlignment(.center)
                        .onChange(of: specificDay) { _, newValue in
                            let clamped = max(1, min(28, newValue))
                            if clamped != newValue { specificDay = clamped }
                            selection = .day(clamped)
                        }

                    Stepper("", value: $specificDay, in: 1...28)
                        .labelsHidden()
                        .onChange(of: specificDay) { _, newValue in
                            selection = .day(newValue)
                        }

                    Spacer()

                    Text("(1–28)")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }

            // Contextual description
            Text(descriptionText)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .glassCard()
        .animation(.easeInOut(duration: 0.2), value: activeSegment)
    }

    private var segmentBinding: Binding<Segment> {
        Binding(
            get: { activeSegment },
            set: { newSeg in
                withAnimation(.easeInOut(duration: 0.2)) {
                    switch newSeg {
                    case .first:
                        selection = .day(1)
                    case .last:
                        selection = .last
                    case .specific:
                        // Restore the last specific value (default 15 if none set yet)
                        let day = specificDay == 1 ? 15 : specificDay
                        specificDay = day
                        selection = .day(day)
                    }
                }
            }
        )
    }

    private var descriptionText: String {
        switch selection {
        case .day(1):
            return "Your budget period begins on the 1st of each calendar month."
        case .last:
            return "Your budget period begins on the last day of each calendar month."
        case .day(let n):
            return "Your budget period begins on the \(ordinal(n)) of each calendar month."
        }
    }

    private func ordinal(_ n: Int) -> String {
        let suffix: String
        switch n % 100 {
        case 11, 12, 13: suffix = "th"
        default:
            switch n % 10 {
            case 1: suffix = "st"
            case 2: suffix = "nd"
            case 3: suffix = "rd"
            default: suffix = "th"
            }
        }
        return "\(n)\(suffix)"
    }
}

// MARK: - ViewModel

@MainActor
class BudgetPeriodViewModel: ObservableObject {
    @Published var monthStartDay: MonthStartDay = .day(1)
    /// Retained specific-day scratch value so switching modes preserves the user's pick.
    @Published var specificDay: Int = 15
    @Published var isLoading = false
    @Published var isSaving = false
    @Published var saveSuccess = false
    @Published var errorMessage: String?

    func loadSettings() async {
        isLoading = true
        errorMessage = nil
        do {
            let settings = try await UserSettingsService.getSettings()
            monthStartDay = settings.budgetMonthStartDay
            // Seed specificDay from the loaded value if it's a concrete day number.
            if case .day(let n) = settings.budgetMonthStartDay, n != 1 {
                specificDay = n
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func save() async {
        isSaving = true
        errorMessage = nil
        saveSuccess = false
        do {
            let request = UserSettingsUpdateRequest(budgetMonthStartDay: monthStartDay)
            let _ = try await UserSettingsService.updateSettings(request)
            saveSuccess = true
            // Auto-hide success after 2.5s
            Task {
                try? await Task.sleep(for: .seconds(2.5))
                saveSuccess = false
            }
        } catch {
            errorMessage = "Failed to save: \(error.localizedDescription)"
        }
        isSaving = false
    }
}
