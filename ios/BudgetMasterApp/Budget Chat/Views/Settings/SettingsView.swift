import SwiftUI

struct SettingsView: View {
    @State private var selectedTab: Int

    init(initialTab: Int = 0) {
        _selectedTab = State(initialValue: initialTab)
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Segmented picker
                Picker("Settings", selection: $selectedTab) {
                    Text("Profile").tag(0)
                    Text("Appearance").tag(1)
                    Text("Categories").tag(2)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.top, 8)
                .padding(.bottom, 4)

                // Tab content
                Group {
                    switch selectedTab {
                    case 0:
                        ProfileTab()
                    case 1:
                        AppearanceTab()
                    case 2:
                        CategoriesTab()
                    default:
                        ProfileTab()
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AuthenticationManager())
        .environmentObject(ThemeManager())
}
