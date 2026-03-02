import SwiftUI
import BudgetMaster

// MARK: - ExclusionsStepView

/// Lets the user choose which categories are excluded from the overall
/// total budget. Excluded categories still carry individual caps but do not
/// count toward the monthly total progress bar.
struct ExclusionsStepView: View {

    /// The categories the user has selected in the categories step.
    let selectedCategories: [DefaultCategory]
    /// IDs of categories to exclude from the total. Shared upward to OnboardingView.
    @Binding var excludedCategoryIds: Set<String>
    let onContinue: () -> Void
    let onSkipExclusions: () -> Void

    @Environment(\.appAccent) private var appAccent

    // Categories we offer for exclusion (exclude OTHER — it already lives
    // outside the user's explicit allocation).
    private var eligibleCategories: [DefaultCategory] {
        selectedCategories.filter { $0.categoryId.uppercased() != "OTHER" }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                header
                    .padding(.horizontal, 24)
                    .padding(.top, 24)

                explanationCard
                    .padding(.horizontal, 24)

                toggleList
                    .padding(.horizontal, 24)

                actions
                    .padding(.horizontal, 24)
                    .padding(.bottom, 16)
            }
        }
        .scrollDismissesKeyboard(.interactively)
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: 6) {
            Text("Exclude from Total")
                .font(.title2.bold())
            Text("Decide which categories count toward your overall spending limit.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
    }

    // MARK: - Explanation Card

    private var explanationCard: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "info.circle")
                .font(.body)
                .foregroundStyle(appAccent)
                .padding(.top, 1)

            Text("Fixed costs like rent are hard to control month-to-month. Excluding them lets you focus your budget on spending you can actually adjust. Excluded categories still have their own caps — they just do not count toward your overall total.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(16)
        .glassCard(cornerRadius: 14)
    }

    // MARK: - Toggle List

    private var toggleList: some View {
        VStack(spacing: 0) {
            if eligibleCategories.isEmpty {
                Text("No categories to configure.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding()
            } else {
                ForEach(eligibleCategories) { category in
                    exclusionRow(category)

                    if category.id != eligibleCategories.last?.id {
                        Divider()
                            .padding(.leading, 56)
                    }
                }
            }
        }
        .glassCard(cornerRadius: 16)
    }

    private func exclusionRow(_ category: DefaultCategory) -> some View {
        let isExcluded = excludedCategoryIds.contains(category.categoryId)

        return HStack(spacing: 12) {
            Image(systemName: AppTheme.sfSymbol(for: category.icon))
                .font(.body)
                .foregroundStyle(Color(hex: category.color) ?? .gray)
                .frame(width: 36, height: 36)
                .background((Color(hex: category.color) ?? .gray).opacity(0.12))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 2) {
                Text(category.displayName)
                    .font(.subheadline.weight(.medium))
                Text(isExcluded ? "Not counted in total" : "Counts toward total")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Toggle("", isOn: Binding(
                get: { isExcluded },
                set: { newValue in
                    if newValue {
                        excludedCategoryIds.insert(category.categoryId)
                    } else {
                        excludedCategoryIds.remove(category.categoryId)
                    }
                }
            ))
            .labelsHidden()
            .tint(appAccent)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .contentShape(Rectangle())
        .onTapGesture {
            withAnimation(.spring(response: 0.25, dampingFraction: 0.7)) {
                if excludedCategoryIds.contains(category.categoryId) {
                    excludedCategoryIds.remove(category.categoryId)
                } else {
                    excludedCategoryIds.insert(category.categoryId)
                }
            }
        }
        .accessibilityLabel("\(category.displayName), \(excludedCategoryIds.contains(category.categoryId) ? "excluded" : "included")")
        .accessibilityHint("Double-tap to toggle exclusion from your total budget")
    }

    // MARK: - Actions

    private var actions: some View {
        VStack(spacing: 12) {
            Button {
                onContinue()
            } label: {
                HStack(spacing: 6) {
                    Text("Continue")
                    Image(systemName: "chevron.right")
                }
                .font(.body.weight(.semibold))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(appAccent)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .accessibilityLabel("Continue to review")

            Button {
                onSkipExclusions()
            } label: {
                Text("Do not exclude anything")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
