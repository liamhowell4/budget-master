import SwiftUI
import FirebaseCore
import FirebaseAuth

@main
struct BudgetMasterApp: App {

    @StateObject private var authManager: AuthenticationManager

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
        NSLog("🚀 BudgetMasterApp: init() complete")
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
        }
    }
}
