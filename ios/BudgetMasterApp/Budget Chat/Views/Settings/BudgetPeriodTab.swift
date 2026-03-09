import SwiftUI
import BudgetMaster

struct BudgetPeriodTab: View {
    @StateObject private var viewModel = BudgetPeriodViewModel()
    @Environment(\.appAccent) private var appAccent

    private let dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Info callout
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: "info.circle.fill")
                        .foregroundStyle(appAccent)
                        .font(.body)
                    Text("Changing your period only changes how your budget is tracked. Your monthly caps stay the same.")
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

                // Period type selection
                VStack(spacing: 8) {
                    HStack {
                        Text("Period Type")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)
                        Spacer()
                    }
                    .padding(.horizontal, 4)

                    VStack(spacing: 0) {
                        periodOption(
                            type: "monthly",
                            icon: "calendar",
                            label: "Monthly",
                            description: "Track spending over a calendar-style month."
                        )
                        Divider().padding(.leading, 52)
                        periodOption(
                            type: "weekly",
                            icon: "calendar.day.timeline.left",
                            label: "Weekly",
                            description: "Monthly budget automatically split into weekly windows."
                        )
                        Divider().padding(.leading, 52)
                        periodOption(
                            type: "biweekly",
                            icon: "calendar.badge.clock",
                            label: "Biweekly",
                            description: "Monthly budget automatically split into biweekly windows."
                        )
                    }
                    .glassCard()
                }

                // Conditional sub-options
                if viewModel.periodType == "monthly" {
                    monthStartDayPicker
                } else if viewModel.periodType == "weekly" {
                    weekStartDayPicker
                } else if viewModel.periodType == "biweekly" {
                    biweeklyAnchorPicker
                }

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

    // MARK: - Period Option Row

    private func periodOption(type: String, icon: String, label: String, description: String) -> some View {
        let isSelected = viewModel.periodType == type

        return Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                viewModel.periodType = type
            }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.body)
                    .foregroundStyle(isSelected ? appAccent : .secondary)
                    .frame(width: 36, height: 36)
                    .background((isSelected ? appAccent : Color(uiColor: .secondarySystemFill)).opacity(0.15))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                VStack(alignment: .leading, spacing: 2) {
                    Text(label)
                        .font(.subheadline)
                        .fontWeight(isSelected ? .medium : .regular)
                        .foregroundStyle(.primary)
                    Text(description)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(appAccent)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    // MARK: - Monthly: Start Day Picker

    private var monthStartDayPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("What day does your budget month start?")
                .font(.subheadline)
                .fontWeight(.medium)
            Text("Align with your pay day. (1-28)")
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack {
                TextField("Day", value: $viewModel.monthStartDay, format: .number)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 80)
                    .onChange(of: viewModel.monthStartDay) { _, newValue in
                        viewModel.monthStartDay = max(1, min(28, newValue))
                    }

                Stepper("", value: $viewModel.monthStartDay, in: 1...28)
                    .labelsHidden()
            }
        }
        .padding(16)
        .glassCard()
    }

    // MARK: - Weekly: Start Day Picker

    private var weekStartDayPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("What day does your week start?")
                .font(.subheadline)
                .fontWeight(.medium)

            FlowLayout(spacing: 8) {
                ForEach(dayNames, id: \.self) { day in
                    let isSelected = viewModel.weekStartDay == day
                    Button {
                        viewModel.weekStartDay = day
                    } label: {
                        Text(String(day.prefix(3)))
                            .font(.caption.weight(.medium))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(isSelected ? appAccent.opacity(0.15) : Color(uiColor: .secondarySystemFill))
                            .foregroundStyle(isSelected ? appAccent : .primary)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(isSelected ? appAccent : .clear, lineWidth: 1.5)
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(16)
        .glassCard()
    }

    // MARK: - Biweekly: Anchor Date Picker

    private var biweeklyAnchorPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("When does your next pay period start?")
                .font(.subheadline)
                .fontWeight(.medium)
            Text("Future pay periods will repeat every 14 days from this date.")
                .font(.caption)
                .foregroundStyle(.secondary)

            DatePicker(
                "Anchor date",
                selection: Binding(
                    get: {
                        let formatter = DateFormatter()
                        formatter.dateFormat = "yyyy-MM-dd"
                        return formatter.date(from: viewModel.biweeklyAnchor) ?? Date()
                    },
                    set: { newDate in
                        let formatter = DateFormatter()
                        formatter.dateFormat = "yyyy-MM-dd"
                        viewModel.biweeklyAnchor = formatter.string(from: newDate)
                    }
                ),
                displayedComponents: .date
            )
            .datePickerStyle(.compact)
            .labelsHidden()
        }
        .padding(16)
        .glassCard()
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
                    .foregroundStyle(appAccent)
            }
        }
        .padding(12)
        .glassCard()
    }
}

// MARK: - ViewModel

@MainActor
class BudgetPeriodViewModel: ObservableObject {
    @Published var periodType: String = "monthly"
    @Published var monthStartDay: Int = 1
    @Published var weekStartDay: String = "Monday"
    @Published var biweeklyAnchor: String = ""
    @Published var isLoading = false
    @Published var isSaving = false
    @Published var saveSuccess = false
    @Published var errorMessage: String?

    func loadSettings() async {
        isLoading = true
        errorMessage = nil
        do {
            let settings = try await UserSettingsService.getSettings()
            periodType = settings.budgetPeriodType
            monthStartDay = settings.budgetMonthStartDay
            weekStartDay = settings.budgetWeekStartDay
            biweeklyAnchor = settings.budgetBiweeklyAnchor
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
            let request = UserSettingsUpdateRequest(
                budgetPeriodType: periodType,
                budgetMonthStartDay: monthStartDay,
                budgetWeekStartDay: weekStartDay,
                budgetBiweeklyAnchor: biweeklyAnchor
            )
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
