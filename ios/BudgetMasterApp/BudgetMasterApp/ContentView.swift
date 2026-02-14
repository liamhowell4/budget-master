import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @State private var selectedTab = 0
    
    var body: some View {
        Group {
            if authManager.isAuthenticated {
                TabView(selection: $selectedTab) {
                    DashboardView()
                        .tabItem {
                            Label("Dashboard", systemImage: "chart.pie.fill")
                        }
                        .tag(0)
                    
                    ExpensesView()
                        .tabItem {
                            Label("Expenses", systemImage: "dollarsign.circle.fill")
                        }
                        .tag(1)
                    
                    ChatView()
                        .tabItem {
                            Label("Chat", systemImage: "message.fill")
                        }
                        .tag(2)
                }
            } else {
                LoginView()
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AuthenticationManager())
}
