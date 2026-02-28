import SwiftUI

/// Circular progress ring showing monthly budget usage.
///
/// Color coding:
/// - Green  < 50 %
/// - Yellow 50–89 %
/// - Orange 90–99 %
/// - Red    100 %+
struct BudgetRingView: View {

    /// Fractional usage, e.g. 0.72 means 72 %. Values > 1.0 are clamped for the arc.
    let percentage: Double

    private var ringColor: Color {
        switch percentage {
        case ..<0.5:  return .green
        case 0.5..<0.9: return .yellow
        case 0.9..<1.0: return .orange
        default:         return .red
        }
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.secondary.opacity(0.2), lineWidth: 4)

            Circle()
                .trim(from: 0, to: min(percentage, 1.0))
                .stroke(
                    ringColor,
                    style: StrokeStyle(lineWidth: 4, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut(duration: 0.5), value: percentage)

            Text("\(Int(percentage * 100))%")
                .font(.system(size: 10, weight: .semibold, design: .rounded))
                .foregroundStyle(ringColor)
        }
    }
}
