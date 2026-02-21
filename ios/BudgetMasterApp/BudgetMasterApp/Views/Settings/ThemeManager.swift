import SwiftUI

// MARK: - Color Scheme Definition

struct ThemeColorScheme: Identifiable {
    let id: String
    let label: String
    let description: String
    let mode: ColorSchemeMode
    let accentColor: Color
    let tintColor: Color

    enum ColorSchemeMode: String {
        case light, dark
    }
}

// MARK: - All Available Schemes

extension ThemeColorScheme {
    static let allSchemes: [ThemeColorScheme] = [
        // Light schemes
        .init(
            id: "light-original",
            label: "Original",
            description: "Clean neutral grays",
            mode: .light,
            accentColor: Color(hex: 0x3B82F6),
            tintColor: Color(hex: 0x3B82F6)
        ),
        .init(
            id: "light-apple",
            label: "Apple",
            description: "iOS-inspired, subtle blue",
            mode: .light,
            accentColor: Color(hex: 0x007AFF),
            tintColor: Color(hex: 0x007AFF)
        ),
        .init(
            id: "light-vibrant",
            label: "Vibrant",
            description: "Bold RGB primaries",
            mode: .light,
            accentColor: Color(hex: 0x2563EB),
            tintColor: Color(hex: 0x2563EB)
        ),
        .init(
            id: "light-glass",
            label: "Glass",
            description: "Frosted blur effects",
            mode: .light,
            accentColor: Color(hex: 0x6366F1),
            tintColor: Color(hex: 0x6366F1)
        ),
        .init(
            id: "light-soft",
            label: "Soft",
            description: "Muted pastels, calming",
            mode: .light,
            accentColor: Color(hex: 0x8B9A83),
            tintColor: Color(hex: 0x8B9A83)
        ),
        .init(
            id: "light-liquid",
            label: "Liquid",
            description: "iOS 26 style, specular shine",
            mode: .light,
            accentColor: Color(hex: 0x007AFF),
            tintColor: Color(hex: 0x007AFF)
        ),

        // Dark schemes
        .init(
            id: "dark-original",
            label: "Original",
            description: "Neutral + purple/orange glow",
            mode: .dark,
            accentColor: Color(hex: 0x818CF8),
            tintColor: Color(hex: 0x818CF8)
        ),
        .init(
            id: "dark-midnight",
            label: "Midnight",
            description: "Deep purple accents",
            mode: .dark,
            accentColor: Color(hex: 0x8B5CF6),
            tintColor: Color(hex: 0x8B5CF6)
        ),
        .init(
            id: "dark-sunset",
            label: "Sunset",
            description: "Warm orange/coral",
            mode: .dark,
            accentColor: Color(hex: 0xF97316),
            tintColor: Color(hex: 0xF97316)
        ),
        .init(
            id: "dark-glass",
            label: "Glass",
            description: "Frosted blur effects",
            mode: .dark,
            accentColor: Color(hex: 0xA78BFA),
            tintColor: Color(hex: 0xA78BFA)
        ),
        .init(
            id: "dark-liquid",
            label: "Liquid",
            description: "iOS 26 style, specular shine",
            mode: .dark,
            accentColor: Color(hex: 0x0A84FF),
            tintColor: Color(hex: 0x0A84FF)
        ),
    ]

    static let lightSchemes: [ThemeColorScheme] = allSchemes.filter { $0.mode == .light }
    static let darkSchemes: [ThemeColorScheme] = allSchemes.filter { $0.mode == .dark }

    static func scheme(for id: String) -> ThemeColorScheme? {
        allSchemes.first { $0.id == id }
    }
}

// MARK: - Theme Manager

final class ThemeManager: ObservableObject {

    // MARK: Persisted preferences

    @AppStorage("useSystemTheme") var useSystemTheme: Bool = true
    @AppStorage("preferredLightTheme") var preferredLightTheme: String = "light-original"
    @AppStorage("preferredDarkTheme") var preferredDarkTheme: String = "dark-original"
    @AppStorage("manualTheme") var manualTheme: String = "light-original"

    // MARK: Computed properties

    /// The scheme ID that is currently active, resolved from system appearance
    /// when `useSystemTheme` is true, or from `manualTheme` otherwise.
    func activeScheme(systemColorScheme: ColorScheme) -> ThemeColorScheme {
        let id: String
        if useSystemTheme {
            id = systemColorScheme == .dark ? preferredDarkTheme : preferredLightTheme
        } else {
            id = manualTheme
        }
        return ThemeColorScheme.scheme(for: id)
            ?? ThemeColorScheme.allSchemes[0]
    }

    /// The SwiftUI `ColorScheme` the app should present.
    /// Returns `nil` when tracking the system (lets the OS decide).
    var activeColorScheme: ColorScheme? {
        guard !useSystemTheme else { return nil }
        guard let scheme = ThemeColorScheme.scheme(for: manualTheme) else { return nil }
        return scheme.mode == .dark ? .dark : .light
    }
}

// MARK: - Color hex initializer

extension Color {
    init(hex: UInt, alpha: Double = 1.0) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255.0,
            green: Double((hex >> 8) & 0xFF) / 255.0,
            blue: Double(hex & 0xFF) / 255.0,
            opacity: alpha
        )
    }
}
