// MARK: - Package Dependency Note
// GoogleSignIn SDK must be added via Xcode > File > Add Package Dependencies
// Package URL: https://github.com/google/GoogleSignIn-iOS
// Select product: GoogleSignIn

import SwiftUI
import FirebaseCore
import FirebaseAuth
import GoogleSignIn
import BudgetMaster

@main
struct BudgetMasterApp: App {

    @StateObject private var authManager: AuthenticationManager
    @StateObject private var themeManager = ThemeManager()

    init() {
        NSLog("==================================================")
        NSLog("🚀 APP STARTING - BudgetMasterApp init()")
        NSLog("==================================================")

        // Configure Firebase before anything else, then init the auth manager.
        NSLog("🚀 BudgetMasterApp: calling FirebaseApp.configure()")

        // Check if GoogleService-Info.plist exists
        if Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") != nil {
            NSLog("✅ GoogleService-Info.plist found")
        } else {
            NSLog("❌ WARNING: GoogleService-Info.plist NOT FOUND!")
        }

        FirebaseApp.configure()

        // Configure Google Sign-In using the CLIENT_ID from GoogleService-Info.plist.
        // This must happen after FirebaseApp.configure() so FirebaseApp.app()?.options is populated.
        if let clientID = FirebaseApp.app()?.options.clientID {
            let config = GIDConfiguration(clientID: clientID)
            GIDSignIn.sharedInstance.configuration = config
            NSLog("✅ GIDSignIn configured with clientID")
        } else {
            NSLog("❌ WARNING: Could not read clientID for GIDSignIn configuration")
        }

        NSLog("🚀 BudgetMasterApp: Firebase configured, creating AuthenticationManager")
        _authManager = StateObject(wrappedValue: AuthenticationManager())

        // Configure BudgetMaster package's APIClient with the correct URL and Firebase auth.
        // On simulator (DEBUG), probes localhost:8000 first and falls back to production.
        // resolvedBaseURL starts as prod so early API calls succeed during the probe.
        Task(priority: .userInitiated) {
            let apiURL = await AppConfiguration.resolveBaseURL()
            AppConfiguration.shared.updateResolvedBaseURL(apiURL.absoluteString)
            await APIClient.shared.setBaseURL(apiURL)
            await APIClient.shared.setTokenProvider(FirebaseTokenProvider())
        }
        // Activate WCSession early so the Watch receives its token as soon as possible.
        _ = WatchSessionManager.shared
        NSLog("🚀 BudgetMasterApp: init() complete")
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(themeManager)
                .preferredColorScheme(themeManager.activeColorScheme)
                // Handle the redirect URL that Google Sign-In sends back after the OAuth flow.
                // Without this, returning from Safari/ASWebAuthenticationSession won't complete sign-in.
                .onOpenURL { url in
                    GIDSignIn.sharedInstance.handle(url)
                }
                // Re-send the token whenever the user signs in or out.
                .onChange(of: authManager.isAuthenticated) { _, isAuthenticated in
                    if isAuthenticated {
                        WatchSessionManager.shared.sendTokenToWatch()
                    }
                }
        }
    }
}
