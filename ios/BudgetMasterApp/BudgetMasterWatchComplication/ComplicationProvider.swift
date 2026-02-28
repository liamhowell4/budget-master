import WidgetKit
import SwiftUI

// MARK: - Timeline Entry

struct BudgetEntry: TimelineEntry {
    let date: Date
    /// Fractional budget usage, e.g. 0.72 = 72 %. 0.0 if unknown.
    let percentage: Double
}

// MARK: - Timeline Provider

struct BudgetComplicationProvider: TimelineProvider {

    typealias Entry = BudgetEntry

    func placeholder(in context: Context) -> BudgetEntry {
        BudgetEntry(date: Date(), percentage: 0.45)
    }

    func getSnapshot(in context: Context, completion: @escaping (BudgetEntry) -> Void) {
        completion(BudgetEntry(date: Date(), percentage: cachedPercentage))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<BudgetEntry>) -> Void) {
        let entry = BudgetEntry(date: Date(), percentage: cachedPercentage)
        // Refresh the complication every hour; the Watch app also calls
        // WidgetCenter.shared.reloadAllTimelines() after each expense submission.
        let nextUpdate = Calendar.current.date(byAdding: .hour, value: 1, to: Date())!
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        completion(timeline)
    }

    /// Reads the budget percentage cached by the Watch app.
    ///
    /// - Note: Requires an App Group (`group.com.liamhowell.budgetmaster.watch`) shared
    ///   between `BudgetMasterWatch` and `BudgetMasterWatchComplication` targets for the
    ///   value to reflect real data. Without App Groups, this falls back to 0.
    private var cachedPercentage: Double {
        // App Group suite (add capability in Xcode for real data sharing):
        // let defaults = UserDefaults(suiteName: "group.com.liamhowell.budgetmaster.watch")
        // return defaults?.double(forKey: "watch.budget.percentage") ?? 0
        return UserDefaults.standard.double(forKey: "watch.budget.percentage")
    }
}

// MARK: - Complication Widget

struct BudgetCircularComplication: Widget {

    let kind = "BudgetCircularComplication"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: BudgetComplicationProvider()) { entry in
            BudgetComplicationView(entry: entry)
                .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Budget")
        .description("Shows your monthly budget usage.")
        .supportedFamilies([.accessoryCircular])
    }
}

// MARK: - Complication View

struct BudgetComplicationView: View {

    let entry: BudgetEntry

    private var ringColor: Color {
        switch entry.percentage {
        case ..<0.5:     return .green
        case 0.5..<0.9:  return .yellow
        case 0.9..<1.0:  return .orange
        default:          return .red
        }
    }

    var body: some View {
        // Deep-link taps open the Watch app directly into RecordView
        Link(destination: URL(string: "budgetmaster://record")!) {
            if entry.percentage > 0 {
                Gauge(value: min(entry.percentage, 1.0)) {
                    Image(systemName: "mic.fill")
                }
                .gaugeStyle(.accessoryCircular)
                .tint(ringColor)
            } else {
                Image(systemName: "mic.fill")
                    .font(.title3)
            }
        }
    }
}
