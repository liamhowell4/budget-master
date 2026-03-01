import SwiftUI
import BudgetMaster

/// Right swipe page — shows the most recent expenses for the current month.
///
/// Data is owned by `WatchDataStore` (injected via `.environmentObject`) so it
/// survives page swipes and is never re-fetched on every appearance.
struct RecentExpensesPageView: View {

    @EnvironmentObject private var dataStore: WatchDataStore

    private let categoryColors: [String: Color] = [
        "FOOD_OUT":   .orange,
        "COFFEE":     .brown,
        "GROCERIES":  .green,
        "GAS":        .yellow,
        "RENT":       .blue,
        "UTILITIES":  .cyan,
        "MEDICAL":    .red,
        "RIDE_SHARE": .purple,
        "HOTEL":      .indigo,
        "TECH":       .teal,
        "TRAVEL":     .mint,
        "OTHER":      .gray,
    ]

    var body: some View {
        Group {
            if dataStore.expensesLoading {
                ProgressView()
            } else if let error = dataStore.expensesError {
                VStack(spacing: 8) {
                    Text(error)
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 6)
                    Button("Retry") {
                        Task { await dataStore.loadExpenses() }
                    }
                    .font(.caption2)
                }
            } else if dataStore.expenses.isEmpty {
                VStack(spacing: 6) {
                    Image(systemName: "tray")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                    Text("No expenses\nthis month")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
            } else {
                List(dataStore.expenses) { expense in
                    expenseRow(expense)
                }
                .listStyle(.plain)
            }
        }
        // Pull-to-refresh reloads only the expenses slice, not budget.
        .refreshable { await dataStore.loadExpenses() }
    }

    // MARK: - Row

    private func expenseRow(_ expense: Expense) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(categoryColors[expense.category.uppercased()] ?? .gray)
                .frame(width: 7, height: 7)

            VStack(alignment: .leading, spacing: 1) {
                Text(expense.expenseName)
                    .font(.caption2)
                    .lineLimit(1)
                Text("\(expense.date.month)/\(expense.date.day)")
                    .font(.system(size: 9))
                    .foregroundStyle(.tertiary)
            }

            Spacer()

            Text(String(format: "$%.0f", expense.amount))
                .font(.caption2.bold())
        }
        .padding(.vertical, 1)
    }
}
