import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @EnvironmentObject var themeManager: ThemeManager
    @Environment(\.colorScheme) var colorScheme

    /// nil = not checked yet, true = needs onboarding, false = skip
    @State private var needsOnboarding: Bool?

    private let api = APIService()

    /// The accent color resolved from the active theme scheme, taking the
    /// system color scheme into account when the user follows system appearance.
    var resolvedAccent: Color {
        themeManager.activeScheme(systemColorScheme: colorScheme).accentColor
    }

    var body: some View {
        Group {
            if authManager.isLoading {
                ProgressView()
                    .progressViewStyle(.circular)
                    .scaleEffect(1.5)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if authManager.isAuthenticated {
                if let needsOnboarding {
                    if needsOnboarding {
                        OnboardingView {
                            withAnimation(.spring(response: 0.5, dampingFraction: 0.85)) {
                                self.needsOnboarding = false
                            }
                        }
                    } else {
                        authenticatedView
                    }
                } else {
                    // Checking onboarding status
                    ProgressView("Setting up...")
                        .progressViewStyle(.circular)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            } else {
                LoginView()
            }
        }
        .onChange(of: authManager.isAuthenticated) { _, isAuth in
            if isAuth {
                checkOnboarding()
            } else {
                needsOnboarding = nil
            }
        }
        .onAppear {
            if authManager.isAuthenticated {
                checkOnboarding()
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

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(3)
        }
        // Propagate the resolved theme accent through the environment so every
        // descendant view can read it via @Environment(\.appAccent), and set
        // .tint so interactive controls (toggles, pickers, etc.) pick it up.
        .environment(\.appAccent, resolvedAccent)
        .tint(resolvedAccent)
    }

    // MARK: - Onboarding Check

    private func checkOnboarding() {
        Task {
            do {
                let categories = try await api.fetchCategories()
                await MainActor.run {
                    needsOnboarding = categories.isEmpty
                }
            } catch {
                // If we can't check, skip onboarding to avoid blocking the user
                await MainActor.run {
                    needsOnboarding = false
                }
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AuthenticationManager())
}
