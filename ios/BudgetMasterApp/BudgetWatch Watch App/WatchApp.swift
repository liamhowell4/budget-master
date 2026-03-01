import SwiftUI
import BudgetMaster

@main
struct BudgetMasterWatchApp: App {

    @StateObject private var tokenProvider = WatchTokenProvider.shared

    init() {
        let url = URL(string: "https://expense-tracker-nsz3hblwea-uc.a.run.app")!
        Task(priority: .userInitiated) {
            await APIClient.shared.setBaseURL(url)
            await APIClient.shared.setTokenProvider(WatchTokenProvider.shared)
        }
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if tokenProvider.hasToken {
                    MainTabView()
                } else {
                    NoTokenView()
                }
            }
            .onOpenURL { _ in
                // Complication deep-link (budgetmaster://record).
                // The app is already showing the mic page when token is present;
                // nothing extra is needed beyond bringing the app to foreground.
            }
        }
    }
}

// MARK: - Main Tab View

/// Three-page horizontal swipe layout.
/// Page 0 (left): Budget overview ring + category bars.
/// Page 1 (center, default): Mic recording view.
/// Page 2 (right): Recent expenses list.
struct MainTabView: View {
    @State private var selectedPage: Int = 1

    var body: some View {
        TabView(selection: $selectedPage) {
            BudgetPageView()
                .tag(0)

            NavigationStack {
                RecordView()
            }
            .tag(1)

            RecentExpensesPageView()
                .tag(2)
        }
        .tabViewStyle(.page)
    }
}

// MARK: - No Token View

/// Shown when the Watch has no valid Firebase token yet.
/// Directs the user to open the iPhone app to authenticate.
struct NoTokenView: View {

    @StateObject private var tokenProvider = WatchTokenProvider.shared

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: "iphone.and.arrow.forward")
                .font(.largeTitle)
                .foregroundStyle(.secondary)

            Text("Open BudgetMaster on your iPhone to sign in.")
                .font(.caption2)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .padding()
        // SwiftUI re-evaluates body and swaps to MainTabView when hasToken becomes true.
        .onChange(of: tokenProvider.hasToken) { _, hasToken in
            _ = hasToken
        }
    }
}
