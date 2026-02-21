import SwiftUI

struct AppearanceTab: View {
    @EnvironmentObject var themeManager: ThemeManager
    @Environment(\.colorScheme) private var systemColorScheme
    @Environment(\.appAccent) private var appAccent

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // System theme toggle
                systemThemeToggle

                if themeManager.useSystemTheme {
                    // Separate pickers for light and dark
                    themeSectionHeader("Light Theme")
                    themeGrid(
                        schemes: ThemeColorScheme.lightSchemes,
                        selectedId: themeManager.preferredLightTheme
                    ) { id in
                        themeManager.preferredLightTheme = id
                    }

                    themeSectionHeader("Dark Theme")
                    themeGrid(
                        schemes: ThemeColorScheme.darkSchemes,
                        selectedId: themeManager.preferredDarkTheme
                    ) { id in
                        themeManager.preferredDarkTheme = id
                    }
                } else {
                    // Single picker for manual mode
                    themeSectionHeader("Light Themes")
                    themeGrid(
                        schemes: ThemeColorScheme.lightSchemes,
                        selectedId: themeManager.manualTheme
                    ) { id in
                        themeManager.manualTheme = id
                    }

                    themeSectionHeader("Dark Themes")
                    themeGrid(
                        schemes: ThemeColorScheme.darkSchemes,
                        selectedId: themeManager.manualTheme
                    ) { id in
                        themeManager.manualTheme = id
                    }
                }
            }
            .padding()
        }
    }

    // MARK: - System Theme Toggle

    private var systemThemeToggle: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Follow System Appearance")
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text("Automatically switch between light and dark themes")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Toggle("", isOn: $themeManager.useSystemTheme)
                .labelsHidden()
                .tint(appAccent)
        }
        .padding()
        .glassCard()
    }

    // MARK: - Theme Section Header

    private func themeSectionHeader(_ title: String) -> some View {
        HStack {
            Text(title)
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Theme Grid

    private func themeGrid(
        schemes: [ThemeColorScheme],
        selectedId: String,
        onSelect: @escaping (String) -> Void
    ) -> some View {
        let columns = [
            GridItem(.flexible(), spacing: 12),
            GridItem(.flexible(), spacing: 12)
        ]

        return LazyVGrid(columns: columns, spacing: 12) {
            ForEach(schemes) { scheme in
                themeSwatch(scheme: scheme, isSelected: scheme.id == selectedId) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        onSelect(scheme.id)
                    }
                }
            }
        }
    }

    // MARK: - Theme Swatch

    private func themeSwatch(
        scheme: ThemeColorScheme,
        isSelected: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 10) {
                // Color preview bar
                HStack(spacing: 6) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(scheme.accentColor)
                        .frame(height: 32)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(scheme.tintColor.opacity(0.5))
                        .frame(width: 24, height: 32)
                }

                VStack(spacing: 2) {
                    Text(scheme.label)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.primary)

                    Text(scheme.description)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            .padding(12)
            .glassCard(cornerRadius: 14)
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isSelected ? scheme.accentColor : .clear, lineWidth: 2)
            )
            .overlay(alignment: .topTrailing) {
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(scheme.accentColor)
                        .padding(8)
                }
            }
        }
        .buttonStyle(.plain)
    }
}
