import SwiftUI
import FirebaseCore
import FirebaseAuth
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
        NSLog("🚀 BudgetMasterApp: Firebase configured, creating AuthenticationManager")
        _authManager = StateObject(wrappedValue: AuthenticationManager())

        // Configure BudgetMaster package's APIClient with the correct URL and Firebase auth
        let apiURL = URL(string: AppConfiguration.shared.apiBaseURL)!
        Task {
            await APIClient.shared.setBaseURL(apiURL)
            await APIClient.shared.setTokenProvider(FirebaseTokenProvider())
        }
        NSLog("🚀 BudgetMasterApp: init() complete")
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(themeManager)
                .preferredColorScheme(themeManager.activeColorScheme)
        }
    }
}
