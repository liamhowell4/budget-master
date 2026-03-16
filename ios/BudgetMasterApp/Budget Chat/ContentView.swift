import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @EnvironmentObject var themeManager: ThemeManager
    @Environment(\.colorScheme) var colorScheme

    /// nil = not checked yet, true = needs onboarding, false = skip
    @State private var needsOnboarding: Bool?
    @State private var selectedTab: Int = 1

    /// Pending prompt to prefill in the chat input on the next chat tab appearance.
    @State private var pendingChatPrefill: String?

    /// What's New modal data — non-nil means we should show the sheet.
    @State private var whatsNewData: WhatsNewData?

    @StateObject private var dashboardViewModel = DashboardViewModel()

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
                launchImageView
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
                    launchImageView
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

    // MARK: - Launch Image

    private var launchImageView: some View {
        GeometryReader { geo in
            Image("LaunchImage")
                .resizable()
                .scaledToFill()
                .frame(width: geo.size.width, height: geo.size.height)
                .clipped()
        }
        .ignoresSafeArea()
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
                DashboardView(viewModel: dashboardViewModel)
                    .tabItem { Label("Dashboard", systemImage: "chart.pie") }
                    .tag(0)
                    .toolbarBackground(resolvedScheme.backgroundTint, for: .tabBar)
                    .toolbarBackground(.visible, for: .tabBar)

                ChatView(pendingPrefill: $pendingChatPrefill)
                    .tabItem { Label("Chat", systemImage: "message.fill") }
                    .tag(1)
                    .toolbarBackground(resolvedScheme.backgroundTint, for: .tabBar)
                    .toolbarBackground(.visible, for: .tabBar)

                ExpensesView()
                    .tabItem { Label("Expenses", systemImage: "dollarsign.circle") }
                    .tag(2)
                    .toolbarBackground(resolvedScheme.backgroundTint, for: .tabBar)
                    .toolbarBackground(.visible, for: .tabBar)
            }
            .onReceive(NotificationCenter.default.publisher(for: .prefillChatPrompt)) { notification in
                guard let prompt = notification.object as? String else { return }
                pendingChatPrefill = prompt
                withAnimation { selectedTab = 1 }
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
        .task {
            await dashboardViewModel.loadData()
        }
        .onAppear {
            if whatsNewData == nil {
                whatsNewData = WhatsNewConfig.loadIfNeeded()
            }
        }
        .sheet(item: $whatsNewData) { data in
            WhatsNewView(data: data) {
                WhatsNewConfig.markAsSeen(data)
                whatsNewData = nil
            }
            .interactiveDismissDisabled()
        }
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
