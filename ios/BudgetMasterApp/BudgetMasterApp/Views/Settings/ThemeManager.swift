import SwiftUI

// MARK: - Color Scheme Definition

struct ThemeColorScheme: Identifiable {
    let id: String
    let label: String
    let description: String
    let mode: ColorSchemeMode
    let accentColor: Color
    let tintColor: Color

    // Chat bubble and background tokens
    let backgroundTint: Color
    let userBubbleColor: Color
    let userBubbleText: Color
    let aiBubbleColor: Color
    let aiBubbleText: Color

    enum ColorSchemeMode: String {
        case light, dark
    }
}

// MARK: - All Available Schemes

extension ThemeColorScheme {

    // MARK: Light Themes

    private static let lightClassic = ThemeColorScheme(
        id: "light-classic", label: "Classic", description: "Clean, familiar", mode: .light,
        accentColor: Color(hex: 0x3B82F6), tintColor: Color(hex: 0x3B82F6),
        backgroundTint: .clear, userBubbleColor: Color(hex: 0x1E293B), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xF2F2F7),
        aiBubbleText: .primary
    )

    private static let lightCoral = ThemeColorScheme(
        id: "light-coral", label: "Coral", description: "Warm, vibrant", mode: .light,
        accentColor: Color(hex: 0xE11D48), tintColor: Color(hex: 0xE11D48),
        backgroundTint: Color(hex: 0xFFF1F2), userBubbleColor: Color(hex: 0xE11D48), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xFFF5F5), aiBubbleText: .primary
    )

    private static let lightEmerald = ThemeColorScheme(
        id: "light-emerald", label: "Emerald", description: "Fresh, natural", mode: .light,
        accentColor: Color(hex: 0x059669), tintColor: Color(hex: 0x059669),
        backgroundTint: Color(hex: 0xECFDF5), userBubbleColor: Color(hex: 0x059669), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xF0FDF9), aiBubbleText: .primary
    )

    private static let lightAmber = ThemeColorScheme(
        id: "light-amber", label: "Amber", description: "Warm, energetic", mode: .light,
        accentColor: Color(hex: 0xD97706), tintColor: Color(hex: 0xD97706),
        backgroundTint: Color(hex: 0xFFFBEB), userBubbleColor: Color(hex: 0xD97706), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xFFFDF5), aiBubbleText: .primary
    )

    private static let lightOcean = ThemeColorScheme(
        id: "light-ocean", label: "Ocean", description: "Cool, calm", mode: .light,
        accentColor: Color(hex: 0x0891B2), tintColor: Color(hex: 0x0891B2),
        backgroundTint: Color(hex: 0xECFEFF), userBubbleColor: Color(hex: 0x0891B2), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xF0FDFE), aiBubbleText: .primary
    )

    // MARK: Dark Themes

    private static let darkCharcoal = ThemeColorScheme(
        id: "dark-charcoal", label: "Charcoal", description: "Minimal, refined", mode: .dark,
        accentColor: Color(hex: 0xCBD5E1), tintColor: Color(hex: 0xCBD5E1),
        backgroundTint: Color(hex: 0x000000), userBubbleColor: Color(hex: 0x1A2233), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x0C0F14), aiBubbleText: .primary
    )

    private static let darkViolet = ThemeColorScheme(
        id: "dark-violet", label: "Violet", description: "Rich, creative", mode: .dark,
        accentColor: Color(hex: 0xC4B5FD), tintColor: Color(hex: 0xC4B5FD),
        backgroundTint: Color(hex: 0x050212), userBubbleColor: Color(hex: 0x5B21B6), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x0B0620), aiBubbleText: .primary
    )

    private static let darkRose = ThemeColorScheme(
        id: "dark-rose", label: "Rose", description: "Bold, playful", mode: .dark,
        accentColor: Color(hex: 0xFB7DD1), tintColor: Color(hex: 0xFB7DD1),
        backgroundTint: Color(hex: 0x060106), userBubbleColor: Color(hex: 0xBE185D), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x12071A), aiBubbleText: .primary
    )

    private static let darkSunset = ThemeColorScheme(
        id: "dark-sunset", label: "Sunset", description: "Warm, glowing", mode: .dark,
        accentColor: Color(hex: 0xFD8C45), tintColor: Color(hex: 0xFD8C45),
        backgroundTint: Color(hex: 0x080400), userBubbleColor: Color(hex: 0xC2410C), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x130900), aiBubbleText: .primary
    )

    private static let darkOcean = ThemeColorScheme(
        id: "dark-ocean", label: "Ocean", description: "Deep, focused", mode: .dark,
        accentColor: Color(hex: 0x00E5FF), tintColor: Color(hex: 0x00E5FF),
        backgroundTint: Color(hex: 0x000D12), userBubbleColor: Color(hex: 0x0369A1), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x060F14), aiBubbleText: .primary
    )

    private static let darkNeon = ThemeColorScheme(
        id: "dark-neon", label: "Neon", description: "Electric, matrix", mode: .dark,
        accentColor: Color(hex: 0x00FF41), tintColor: Color(hex: 0x00FF41),
        backgroundTint: Color(hex: 0x010301), userBubbleColor: Color(hex: 0x003311), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x050F06), aiBubbleText: .primary
    )

    private static let darkCyber = ThemeColorScheme(
        id: "dark-cyber", label: "Cyber", description: "Neon pink, futuristic", mode: .dark,
        accentColor: Color(hex: 0xFF2D9B), tintColor: Color(hex: 0xFF2D9B),
        backgroundTint: Color(hex: 0x060005), userBubbleColor: Color(hex: 0x6D0050), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x0D0011), aiBubbleText: .primary
    )

    static let allSchemes: [ThemeColorScheme] = [
        lightClassic, lightCoral, lightEmerald, lightAmber, lightOcean,
        darkCharcoal, darkViolet, darkRose, darkSunset, darkOcean, darkNeon, darkCyber,
    ]

    static let lightSchemes: [ThemeColorScheme] = allSchemes.filter { $0.mode == .light }
    static let darkSchemes: [ThemeColorScheme] = allSchemes.filter { $0.mode == .dark }

    static func scheme(for id: String) -> ThemeColorScheme? {
        allSchemes.first { $0.id == id }
    }

    /// The canvas color to use in the Appearance tab swatch preview.
    /// Falls back to a neutral system color for themes whose `backgroundTint`
    /// is `.clear` (i.e., Classic light), since `Color` is not `Equatable`.
    var swatchCanvasColor: Color {
        // Classic light deliberately uses .clear — give the swatch a neutral fill.
        if id == "light-classic" {
            return Color(hex: 0xF2F2F7)
        }
        return backgroundTint
    }
}

// MARK: - Theme Manager

final class ThemeManager: ObservableObject {

    // MARK: Persisted preferences

    @AppStorage("useSystemTheme") var useSystemTheme: Bool = true
    @AppStorage("preferredLightTheme") var preferredLightTheme: String = "light-classic"
    @AppStorage("preferredDarkTheme") var preferredDarkTheme: String = "dark-charcoal"
    @AppStorage("manualTheme") var manualTheme: String = "light-classic"

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
        // Falls back to allSchemes[0] gracefully — handles migration from old theme IDs.
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
