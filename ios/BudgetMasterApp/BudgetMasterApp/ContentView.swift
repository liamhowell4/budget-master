import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager

    var body: some View {
        Group {
            if authManager.isLoading {
                ProgressView()
                    .progressViewStyle(.circular)
                    .scaleEffect(1.5)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if authManager.isAuthenticated {
                authenticatedView
            } else {
                LoginView()
            }
        }
    }

    // MARK: - Authenticated Layout

    private var authenticatedView: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "chart.pie") }
                .tag(0)

            ChatView()
                .tabItem { Label("Chat", systemImage: "message") }
                .tag(1)

            ExpensesView()
                .tabItem { Label("Expenses", systemImage: "dollarsign.circle") }
                .tag(2)
        }
        .tint(AppTheme.accent)
    }
}

#Preview {
    ContentView()
        .environmentObject(AuthenticationManager())
}
