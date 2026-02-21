import SwiftUI
import BudgetMaster

struct AIModelTab: View {
    @StateObject private var viewModel = AIModelViewModel()
    @Environment(\.appAccent) private var appAccent

    private let providers: [(name: String, models: [(key: String, label: String)])] = [
        ("Anthropic", [
            ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
            ("claude-haiku-4-5", "Claude Haiku 4.5"),
        ]),
        ("OpenAI", [
            ("gpt-5-mini", "GPT-5 Mini"),
            ("gpt-5.1", "GPT-5.1"),
        ]),
        ("Google", [
            ("gemini-3.1-pro", "Gemini 3.1 Pro"),
            ("gemini-3-flash", "Gemini 3 Flash"),
        ]),
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                if let error = viewModel.errorMessage {
                    errorBanner(error)
                }

                ForEach(providers, id: \.name) { provider in
                    providerSection(provider)
                }
            }
            .padding()
        }
        .task {
            await viewModel.loadSettings()
        }
        .overlay {
            if viewModel.isLoading && viewModel.selectedModel == nil {
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
                    .foregroundStyle(appAccent)
            }
        }
        .padding(12)
        .glassCard()
    }

    // MARK: - Provider Section

    private func providerSection(_ provider: (name: String, models: [(key: String, label: String)])) -> some View {
        VStack(spacing: 8) {
            HStack {
                Text(provider.name)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)
                Spacer()
            }
            .padding(.horizontal, 4)

            VStack(spacing: 0) {
                ForEach(Array(provider.models.enumerated()), id: \.element.key) { index, model in
                    modelRow(key: model.key, label: model.label)

                    if index < provider.models.count - 1 {
                        Divider()
                            .padding(.leading, 52)
                    }
                }
            }
            .glassCard()
        }
    }

    // MARK: - Model Row

    private func modelRow(key: String, label: String) -> some View {
        let isSelected = viewModel.selectedModel == key
        let isSaving = viewModel.savingModel == key

        return Button {
            Task { await viewModel.selectModel(key) }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: providerIcon(for: key))
                    .font(.body)
                    .foregroundStyle(isSelected ? appAccent : .secondary)
                    .frame(width: 36, height: 36)
                    .background((isSelected ? appAccent : Color(uiColor: .secondarySystemFill)).opacity(0.15))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                Text(label)
                    .font(.subheadline)
                    .fontWeight(isSelected ? .medium : .regular)
                    .foregroundStyle(.primary)

                Spacer()

                if isSaving {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .scaleEffect(0.8)
                } else if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(appAccent)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(viewModel.savingModel != nil)
        .accessibilityLabel(label)
        .accessibilityHint(isSelected ? "Currently selected" : "Tap to select this model")
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }

    private func providerIcon(for key: String) -> String {
        if key.hasPrefix("claude") { return "brain.head.profile" }
        if key.hasPrefix("gpt") { return "sparkles" }
        return "g.circle"
    }
}

// MARK: - ViewModel

@MainActor
class AIModelViewModel: ObservableObject {
    @Published var selectedModel: String?
    @Published var savingModel: String?
    @Published var isLoading = false
    @Published var errorMessage: String?

    func loadSettings() async {
        isLoading = true
        errorMessage = nil
        do {
            let settings = try await UserSettingsService.getSettings()
            selectedModel = settings.selectedModel
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func selectModel(_ model: String) async {
        guard model != selectedModel else { return }
        let previous = selectedModel
        selectedModel = model
        savingModel = model
        errorMessage = nil
        do {
            let updated = try await UserSettingsService.updateModel(model)
            selectedModel = updated.selectedModel
        } catch {
            selectedModel = previous
            errorMessage = error.localizedDescription
        }
        savingModel = nil
    }
}
