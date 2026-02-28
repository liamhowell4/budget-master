import SwiftUI
import WidgetKit
import BudgetMaster

/// Displays the parsed expense details after a successful audio upload.
/// Auto-dismisses after 3 seconds; a "Done" button allows manual dismiss.
struct ConfirmationView: View {

    let response: ExpenseProcessResponse
    let onDismiss: () -> Void

    @Environment(\.dismiss) private var dismiss

    private var categoryIcon: String {
        switch response.category?.uppercased() {
        case "FOOD_OUT":   return "fork.knife"
        case "COFFEE":     return "cup.and.saucer.fill"
        case "GROCERIES":  return "cart.fill"
        case "GAS":        return "fuelpump.fill"
        case "RENT":       return "house.fill"
        case "UTILITIES":  return "bolt.fill"
        case "MEDICAL":    return "cross.fill"
        case "RIDE_SHARE": return "car.fill"
        case "HOTEL":      return "bed.double.fill"
        case "TECH":       return "desktopcomputer"
        case "TRAVEL":     return "airplane"
        default:           return "dollarsign.circle.fill"
        }
    }

    var body: some View {
        VStack(spacing: 6) {
            Image(systemName: categoryIcon)
                .font(.largeTitle)
                .foregroundStyle(.green)

            if let name = response.expenseName {
                Text(name)
                    .font(.headline)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }

            if let amount = response.amount {
                Text(String(format: "$%.2f", amount))
                    .font(.title3.bold())
            }

            if let warning = response.budgetWarning {
                Text(warning)
                    .font(.caption2)
                    .foregroundStyle(.orange)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }

            Button("Done") {
                performDismiss()
            }
            .font(.caption)
        }
        .padding(.horizontal, 4)
        .task {
            // Reload complication timeline so it reflects the new expense
            WidgetCenter.shared.reloadAllTimelines()

            // Auto-dismiss after 3 seconds
            try? await Task.sleep(for: .seconds(3))
            performDismiss()
        }
    }

    private func performDismiss() {
        onDismiss()
        dismiss()
    }
}
