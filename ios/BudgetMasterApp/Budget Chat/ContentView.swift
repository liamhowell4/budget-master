import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @EnvironmentObject var themeManager: ThemeManager
    @Environment(\.colorScheme) var colorScheme

    /// nil = not checked yet, true = needs onboarding, false = skip
    @State private var needsOnboarding: Bool?
    @State private var selectedTab: Int = 1

    private let api = APIService()

    /// The full scheme resolved from system appearance (or manual override).
    var resolvedScheme: ThemeColorScheme {
        themeManager.activeScheme(systemColorScheme: colorScheme)
    }

    /// Convenience accessor so downstream callsites remain unchanged.
    var resolvedAccent: Color {
        resolvedScheme.accentColor
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
        // ZStack wrapping the TabView so SwiftUI — not UIKit — owns the
        // background layer. Applying .background() directly on a TabView targets
        // the UITabBarController's UIView.backgroundColor, which UIKit manages
        // independently of SwiftUI's layout/diffing pass; it may not update when
        // theme tokens change. Rendering the tint color as a ZStack underlay
        // ensures full reactive re-rendering whenever resolvedScheme changes.
        ZStack {
            resolvedScheme.backgroundTint
                .ignoresSafeArea()

            TabView(selection: $selectedTab) {
                DashboardView()
                    .tabItem { Label("Dashboard", systemImage: "chart.pie") }
                    .tag(0)

                ChatView()
                    .tabItem { Label("Chat", systemImage: "message.fill") }
                    .tag(1)

                ExpensesView()
                    .tabItem { Label("Expenses", systemImage: "dollarsign.circle") }
                    .tag(2)
            }
        }
        // Propagate all resolved theme tokens through the environment so every
        // descendant view can read them via @Environment, and set .tint so
        // interactive controls (toggles, pickers, etc.) pick up the accent.
        .environment(\.appAccent, resolvedAccent)
        .environment(\.appBackgroundTint, resolvedScheme.backgroundTint)
        .environment(\.appUserBubble, resolvedScheme.userBubbleColor)
        .environment(\.appUserBubbleText, resolvedScheme.userBubbleText)
        .environment(\.appAiBubble, resolvedScheme.aiBubbleColor)
        .environment(\.appAiBubbleText, resolvedScheme.aiBubbleText)
        .tint(resolvedAccent)
        .animation(.easeInOut(duration: 0.25), value: resolvedScheme.id)
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
