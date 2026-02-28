import SwiftUI
import BudgetMaster

@main
struct BudgetMasterWatchApp: App {

    @StateObject private var tokenProvider = WatchTokenProvider.shared

    init() {
        // Point APIClient at the production backend and inject the Watch token provider.
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
                    NavigationStack {
                        RecordView()
                    }
                } else {
                    NoTokenView()
                }
            }
            .onOpenURL { _ in
                // Complication deep-link (budgetmaster://record).
                // The app is already showing RecordView when token is present;
                // nothing extra is needed beyond bringing the app to foreground.
            }
        }
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
        // Automatically transition once the token arrives via WCSession
        .onChange(of: tokenProvider.hasToken) { _, hasToken in
            // SwiftUI will re-evaluate body and swap to RecordView when hasToken becomes true
            _ = hasToken
        }
    }
}
