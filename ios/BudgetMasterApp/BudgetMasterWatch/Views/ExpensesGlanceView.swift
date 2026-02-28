import SwiftUI
import BudgetMaster

/// A glanceable list of the last 5 expenses for the current month.
/// Presented as a sheet from RecordView via the "Expenses" button.
struct ExpensesGlanceView: View {

    @State private var expenses: [Expense] = []
    @State private var isLoading = true
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if let error = errorMessage {
                Text(error)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding()
            } else if expenses.isEmpty {
                Text("No expenses this month")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            } else {
                List(expenses) { expense in
                    HStack(spacing: 4) {
                        Text(categoryEmoji(expense.category))
                            .font(.caption)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(expense.expenseName)
                                .font(.caption2)
                                .lineLimit(1)
                            Text("\(expense.date.month)/\(expense.date.day)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Text(String(format: "$%.0f", expense.amount))
                            .font(.caption2.bold())
                    }
                }
            }
        }
        .navigationTitle("Recent")
        .task { await load() }
        .refreshable { await load() }
    }

    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            expenses = try await WatchExpenseService.fetchRecentExpenses()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func categoryEmoji(_ category: String) -> String {
        switch category.uppercased() {
        case "FOOD_OUT":   return "🍽️"
        case "COFFEE":     return "☕️"
        case "GROCERIES":  return "🛒"
        case "GAS":        return "⛽️"
        case "RENT":       return "🏠"
        case "UTILITIES":  return "⚡️"
        case "MEDICAL":    return "💊"
        case "RIDE_SHARE": return "🚗"
        case "HOTEL":      return "🛏️"
        case "TECH":       return "💻"
        case "TRAVEL":     return "✈️"
        default:           return "💰"
        }
    }
}
