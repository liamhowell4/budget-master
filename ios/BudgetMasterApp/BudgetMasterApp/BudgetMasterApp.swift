import SwiftUI
import FirebaseCore
import FirebaseAuth

@main
struct BudgetMasterApp: App {

    @StateObject private var authManager: AuthenticationManager

    init() {
        // Configure Firebase before anything else, then init the auth manager.
        print("🚀 BudgetMasterApp: calling FirebaseApp.configure()")
        FirebaseApp.configure()
        print("🚀 BudgetMasterApp: Firebase configured, creating AuthenticationManager")
        _authManager = StateObject(wrappedValue: AuthenticationManager())
        print("🚀 BudgetMasterApp: init() complete")
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
        }
    }
}
