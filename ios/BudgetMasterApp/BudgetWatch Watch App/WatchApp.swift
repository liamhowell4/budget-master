import SwiftUI
import BudgetMaster

@main
struct BudgetMasterWatchApp: App {

    @StateObject private var tokenProvider = WatchTokenProvider.shared

    init() {
        // Set the base URL at launch. Token provider wiring is deferred to
        // WatchDataStore.load() so it is guaranteed to complete before any
        // network request fires (eliminating the previous race condition).
        let url = URL(string: "https://expense-tracker-nsz3hblwea-uc.a.run.app")!
        Task(priority: .userInitiated) {
            await APIClient.shared.setBaseURL(url)
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
///
/// `dataStore` is a `@StateObject` here so its lifetime matches the tab view —
/// data is fetched once and shared across all pages, preventing duplicate
/// in-flight requests and cancellation when the user swipes between tabs.
struct MainTabView: View {
    @StateObject private var dataStore = WatchDataStore()
    @State private var selectedPage: Int = 1

    var body: some View {
        TabView(selection: $selectedPage) {
            BudgetPageView()
                .environmentObject(dataStore)
                .tag(0)

            NavigationStack {
                RecordView()
            }
            .tag(1)

            RecentExpensesPageView()
                .environmentObject(dataStore)
                .tag(2)
        }
        .tabViewStyle(.page)
        // Single task at the container level: sets auth then fetches both
        // datasets in parallel. SwiftUI cancels this task when MainTabView
        // leaves the hierarchy, which is the correct lifecycle scope.
        .task { await dataStore.load() }
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
