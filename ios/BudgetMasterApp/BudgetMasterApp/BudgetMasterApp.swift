import SwiftUI
import FirebaseCore
import FirebaseAuth

@main
struct BudgetMasterApp: App {
    
    init() {
        // Configure Firebase
        FirebaseApp.configure()
    }
    
    @StateObject private var authManager = AuthenticationManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
        }
    }
}
