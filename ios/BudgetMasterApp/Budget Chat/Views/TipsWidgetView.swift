import SwiftUI

// MARK: - Notification for chat prefill

extension Notification.Name {
    /// Posted when a tips example should prefill the chat input.
    /// The `object` is the prompt String.
    static let prefillChatPrompt = Notification.Name("prefillChatPrompt")
}

// MARK: - TipSection Model

private struct TipSection: Identifiable {
    let id = UUID()
    let title: String
    let icon: String
    let rows: [TipRow]
}

private struct TipRow: Identifiable {
    let id = UUID()
    let prompt: String
    let preview: String
}

// MARK: - TipsWidgetView

/// Collapsible dashboard card showing example prompts grouped by category.
/// "Try this" posts `prefillChatPrompt` via NotificationCenter so ContentView
/// can switch to the chat tab and set the input text without needing a shared
/// ObservableObject threaded through unrelated parts of the tree.
struct TipsWidgetView: View {

    @AppStorage("tipsWidgetExpanded") private var isExpanded: Bool = false
    @Environment(\.appAccent) private var appAccent

    var body: some View {
        VStack(spacing: 0) {
            headerButton
            if isExpanded {
                Divider()
                sectionsContent
            }
        }
        .glassCard(cornerRadius: 16)
        .animation(.spring(response: 0.35, dampingFraction: 0.85), value: isExpanded)
        .clipped()
    }

    // MARK: - Header

    private var headerButton: some View {
        Button {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                isExpanded.toggle()
            }
        } label: {
            HStack {
                Image(systemName: "lightbulb")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(appAccent)
                Text("Tips & Examples")
                    .font(.headline)
                Spacer()
                Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isExpanded)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isExpanded ? "Collapse tips" : "Expand tips")
    }

    // MARK: - Sections Content

    private var sectionsContent: some View {
        VStack(spacing: 0) {
            ForEach(tipSections) { section in
                tipSectionView(section)
                if section.id != tipSections.last?.id {
                    Divider()
                }
            }
        }
    }

    @ViewBuilder
    private func tipSectionView(_ section: TipSection) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            // Section header
            HStack(spacing: 8) {
                Image(systemName: section.icon)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(appAccent)
                Text(section.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 6)

            ForEach(section.rows) { row in
                tipRow(row)
                if row.id != section.rows.last?.id {
                    Divider()
                        .padding(.leading, 16)
                }
            }
        }
    }

    private func tipRow(_ row: TipRow) -> some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(row.prompt)
                    .font(.subheadline)
                    .foregroundStyle(.primary)
                Text(row.preview)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            Button {
                NotificationCenter.default.post(
                    name: .prefillChatPrompt,
                    object: row.prompt
                )
            } label: {
                HStack(spacing: 4) {
                    Text("Try")
                        .font(.caption.weight(.medium))
                    Image(systemName: "arrow.right")
                        .font(.caption2.weight(.semibold))
                }
                .foregroundStyle(appAccent)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .glassCapsule()
            }
            .accessibilityLabel("Try: \(row.prompt)")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Data

    private let tipSections: [TipSection] = [
        TipSection(
            title: "Logging Expenses",
            icon: "plus.circle",
            rows: [
                TipRow(prompt: "Chipotle $14.50 for lunch",
                       preview: "Got it! Logged Chipotle for $14.50 under Food Out."),
                TipRow(prompt: "Groceries $67 at Whole Foods",
                       preview: "Saved! $67.00 at Whole Foods added to Groceries."),
                TipRow(prompt: "Amazon order $34.99",
                       preview: "Added! Amazon Order for $34.99 under Tech."),
            ]
        ),
        TipSection(
            title: "Editing and Deleting",
            icon: "pencil",
            rows: [
                TipRow(prompt: "Delete that last one",
                       preview: "Done — I've deleted the most recent expense."),
                TipRow(prompt: "Change that to $15",
                       preview: "Updated! Changed the amount to $15.00."),
                TipRow(prompt: "Actually it was Whole Foods, not Target",
                       preview: "Fixed! Updated the name to Whole Foods."),
            ]
        ),
        TipSection(
            title: "Analytics",
            icon: "chart.bar",
            rows: [
                TipRow(prompt: "How much on food this month?",
                       preview: "You've spent $312.40 on Food Out this month."),
                TipRow(prompt: "Compare this month to last",
                       preview: "This month: $1,204. Last month: $1,089. Up $115."),
                TipRow(prompt: "Am I on track this month?",
                       preview: "You've used 62% of your budget at day 18."),
            ]
        ),
        TipSection(
            title: "Recurring Expenses",
            icon: "arrow.clockwise",
            rows: [
                TipRow(prompt: "Add rent $1,400 every month",
                       preview: "Created! Rent ($1,400) will be added on the 1st."),
                TipRow(prompt: "List my recurring expenses",
                       preview: "You have 2 recurring: Rent ($1,400/mo), Netflix ($15.99/mo)."),
                TipRow(prompt: "Remove the Netflix recurring",
                       preview: "Done — Netflix recurring removed."),
            ]
        ),
        TipSection(
            title: "Budget Status",
            icon: "creditcard",
            rows: [
                TipRow(prompt: "What's left in my dining budget?",
                       preview: "$87.60 remaining in Food Out (65% used)."),
                TipRow(prompt: "How's my total budget looking?",
                       preview: "$1,204 of $2,000 used this month (60.2%)."),
            ]
        ),
    ]
}
