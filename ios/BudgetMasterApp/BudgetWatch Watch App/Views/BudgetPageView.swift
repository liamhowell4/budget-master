import SwiftUI
import BudgetMaster

/// Left swipe page — shows overall budget ring + per-category progress bars.
///
/// Data is owned by `WatchDataStore` (injected via `.environmentObject`) so it
/// survives page swipes and is never re-fetched on every appearance.
struct BudgetPageView: View {

    @EnvironmentObject private var dataStore: WatchDataStore

    var body: some View {
        Group {
            if dataStore.budgetLoading {
                VStack(spacing: 8) {
                    ProgressView()
                    Text("Budget")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            } else if let budget = dataStore.budgetStatus {
                budgetContent(budget)
            } else {
                VStack(spacing: 10) {
                    Image(systemName: "chart.pie")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                    if let error = dataStore.budgetError {
                        Text(error)
                            .font(.system(size: 9))
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 6)
                    } else {
                        Text("Budget unavailable")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    Button("Retry") {
                        Task { await dataStore.loadBudget() }
                    }
                    .font(.caption2)
                }
            }
        }
    }

    // MARK: - Budget Content

    private func budgetContent(_ budget: BudgetStatus) -> some View {
        ScrollView {
            VStack(spacing: 10) {
                // Month label
                Text(budget.monthName.uppercased())
                    .font(.system(size: 10, weight: .medium, design: .rounded))
                    .foregroundStyle(.secondary)
                    .kerning(0.8)

                // Total ring
                BudgetRingView(percentage: budget.totalPercentage / 100)
                    .frame(width: 62, height: 62)

                // Spending summary
                if budget.totalCap > 0 {
                    Text("$\(Int(budget.totalSpending)) of $\(Int(budget.totalCap))")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }

                // Category rows (only where cap is set)
                let cappedCategories = budget.categories.filter { $0.cap > 0 }
                if !cappedCategories.isEmpty {
                    Divider()
                        .padding(.horizontal, 4)

                    ForEach(cappedCategories) { category in
                        categoryRow(category)
                    }
                }
            }
            .padding(.horizontal, 8)
            .padding(.bottom, 16)
        }
        // Pull-to-refresh reloads only the budget slice, not expenses.
        .refreshable { await dataStore.loadBudget() }
    }

    // MARK: - Category Row

    private func categoryRow(_ category: BudgetCategory) -> some View {
        let pct = category.percentage / 100
        let color = barColor(pct)

        return VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 4) {
                Text(category.emoji)
                    .font(.system(size: 12))
                Text(displayName(category.category))
                    .font(.caption2)
                Spacer()
                Text("\(Int(category.percentage))%")
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(color)
            }

            // Progress bar
            RoundedRectangle(cornerRadius: 2)
                .fill(Color.secondary.opacity(0.2))
                .frame(height: 4)
                .overlay(alignment: .leading) {
                    GeometryReader { geo in
                        RoundedRectangle(cornerRadius: 2)
                            .fill(color)
                            .frame(width: geo.size.width * min(pct, 1.0))
                            .animation(.easeInOut(duration: 0.5), value: pct)
                    }
                }
        }
    }

    // MARK: - Helpers

    private func barColor(_ pct: Double) -> Color {
        switch pct {
        case ..<0.5:       return .green
        case 0.5..<0.9:   return .yellow
        case 0.9..<1.0:   return .orange
        default:           return .red
        }
    }

    private func displayName(_ category: String) -> String {
        switch category.uppercased() {
        case "FOOD_OUT":   return "Dining"
        case "COFFEE":     return "Coffee"
        case "GROCERIES":  return "Groceries"
        case "GAS":        return "Gas"
        case "RENT":       return "Rent"
        case "UTILITIES":  return "Utilities"
        case "MEDICAL":    return "Medical"
        case "RIDE_SHARE": return "Rides"
        case "HOTEL":      return "Hotel"
        case "TECH":       return "Tech"
        case "TRAVEL":     return "Travel"
        case "OTHER":      return "Other"
        default:
            return category
                .replacingOccurrences(of: "_", with: " ")
                .capitalized
        }
    }
}
