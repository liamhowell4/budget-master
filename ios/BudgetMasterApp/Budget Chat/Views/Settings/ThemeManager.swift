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
        backgroundTint: Color(hex: 0xFDE8EB), userBubbleColor: Color(hex: 0xE11D48), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xFFF0F1), aiBubbleText: .primary
    )

    private static let lightEmerald = ThemeColorScheme(
        id: "light-emerald", label: "Emerald", description: "Fresh, natural", mode: .light,
        accentColor: Color(hex: 0x059669), tintColor: Color(hex: 0x059669),
        backgroundTint: Color(hex: 0xDFF5EB), userBubbleColor: Color(hex: 0x059669), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xEAFAF2), aiBubbleText: .primary
    )

    private static let lightAmber = ThemeColorScheme(
        id: "light-amber", label: "Amber", description: "Warm, energetic", mode: .light,
        accentColor: Color(hex: 0xD97706), tintColor: Color(hex: 0xD97706),
        backgroundTint: Color(hex: 0xFFF0D1), userBubbleColor: Color(hex: 0xD97706), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xFFF7E2), aiBubbleText: .primary
    )

    private static let lightOcean = ThemeColorScheme(
        id: "light-ocean", label: "Ocean", description: "Cool, calm", mode: .light,
        accentColor: Color(hex: 0x0891B2), tintColor: Color(hex: 0x0891B2),
        backgroundTint: Color(hex: 0xDBF0F5), userBubbleColor: Color(hex: 0x0891B2), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xE8F6FA), aiBubbleText: .primary
    )

    private static let lightSoft = ThemeColorScheme(
        id: "light-soft", label: "Soft", description: "Warm, calming", mode: .light,
        accentColor: Color(hex: 0x8B9A83), tintColor: Color(hex: 0x8B9A83),
        backgroundTint: Color(hex: 0xF2ECE3), userBubbleColor: Color(hex: 0x8B9A83), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xEDE7DD), aiBubbleText: Color(hex: 0x3D3A36)
    )

    private static let lightGlass = ThemeColorScheme(
        id: "light-glass", label: "Glass", description: "Frosted, airy", mode: .light,
        accentColor: Color(hex: 0x6366F1), tintColor: Color(hex: 0x6366F1),
        backgroundTint: Color(hex: 0xE6ECF4), userBubbleColor: Color(hex: 0x6366F1), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0xDCE3EE), aiBubbleText: Color(hex: 0x0F172A)
    )

    // MARK: Dark Themes

    private static let darkCharcoal = ThemeColorScheme(
        id: "dark-charcoal", label: "Charcoal", description: "Minimal, refined", mode: .dark,
        accentColor: Color(hex: 0xCBD5E1), tintColor: Color(hex: 0xCBD5E1),
        backgroundTint: Color(hex: 0x08090E), userBubbleColor: Color(hex: 0x1A2233), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x10131A), aiBubbleText: .primary
    )

    private static let darkViolet = ThemeColorScheme(
        id: "dark-violet", label: "Violet", description: "Rich, creative", mode: .dark,
        accentColor: Color(hex: 0xC4B5FD), tintColor: Color(hex: 0xC4B5FD),
        backgroundTint: Color(hex: 0x0E0826), userBubbleColor: Color(hex: 0x5B21B6), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x160E32), aiBubbleText: .primary
    )

    private static let darkRose = ThemeColorScheme(
        id: "dark-rose", label: "Rose", description: "Bold, playful", mode: .dark,
        accentColor: Color(hex: 0xFB7DD1), tintColor: Color(hex: 0xFB7DD1),
        backgroundTint: Color(hex: 0x150A18), userBubbleColor: Color(hex: 0xBE185D), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x1E1024), aiBubbleText: .primary
    )

    private static let darkSunset = ThemeColorScheme(
        id: "dark-sunset", label: "Sunset", description: "Warm, glowing", mode: .dark,
        accentColor: Color(hex: 0xFD8C45), tintColor: Color(hex: 0xFD8C45),
        backgroundTint: Color(hex: 0x140A04), userBubbleColor: Color(hex: 0xC2410C), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x1E1208), aiBubbleText: .primary
    )

    private static let darkOcean = ThemeColorScheme(
        id: "dark-ocean", label: "Ocean", description: "Deep, focused", mode: .dark,
        accentColor: Color(hex: 0x00E5FF), tintColor: Color(hex: 0x00E5FF),
        backgroundTint: Color(hex: 0x061620), userBubbleColor: Color(hex: 0x0369A1), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x0C1E2C), aiBubbleText: .primary
    )

    private static let darkNeon = ThemeColorScheme(
        id: "dark-neon", label: "Neon", description: "Electric, matrix", mode: .dark,
        accentColor: Color(hex: 0x00FF41), tintColor: Color(hex: 0x00FF41),
        backgroundTint: Color(hex: 0x041408), userBubbleColor: Color(hex: 0x003311), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x0A1E0E), aiBubbleText: .primary
    )

    private static let darkCyber = ThemeColorScheme(
        id: "dark-cyber", label: "Cyber", description: "Neon pink, futuristic", mode: .dark,
        accentColor: Color(hex: 0xFF2D9B), tintColor: Color(hex: 0xFF2D9B),
        backgroundTint: Color(hex: 0x120814), userBubbleColor: Color(hex: 0x6D0050), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x1C0E20), aiBubbleText: .primary
    )

    private static let darkMidnight = ThemeColorScheme(
        id: "dark-midnight", label: "Midnight", description: "Deep, cosmic", mode: .dark,
        accentColor: Color(hex: 0x8B5CF6), tintColor: Color(hex: 0x8B5CF6),
        backgroundTint: Color(hex: 0x0A0A2A), userBubbleColor: Color(hex: 0x6366F1), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x12123C), aiBubbleText: .primary
    )

    private static let darkCocoa = ThemeColorScheme(
        id: "dark-cocoa", label: "Cocoa", description: "Warm, earthy", mode: .dark,
        accentColor: Color(hex: 0xD4915C), tintColor: Color(hex: 0xD4915C),
        backgroundTint: Color(hex: 0x16100A), userBubbleColor: Color(hex: 0x8B5E3C), userBubbleText: .white,
        aiBubbleColor: Color(hex: 0x201812), aiBubbleText: .primary
    )

    static let allSchemes: [ThemeColorScheme] = [
        lightClassic, lightCoral, lightEmerald, lightAmber, lightOcean, lightSoft, lightGlass,
        darkCharcoal, darkViolet, darkRose, darkSunset, darkOcean, darkNeon, darkCyber, darkMidnight, darkCocoa,
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
    //
    // Theme preferences use @Published so SwiftUI dependency tracking correctly
    // registers re-renders. Each property writes through to UserDefaults in didSet
    // so values survive app restarts. We avoid @AppStorage here because it does not
    // reliably trigger objectWillChange on ObservableObject classes, which caused
    // background colors to not update on theme switch.

    @Published var useSystemTheme: Bool {
        didSet { UserDefaults.standard.set(useSystemTheme, forKey: "useSystemTheme") }
    }

    @Published var preferredLightTheme: String {
        didSet { UserDefaults.standard.set(preferredLightTheme, forKey: "preferredLightTheme") }
    }

    @Published var preferredDarkTheme: String {
        didSet { UserDefaults.standard.set(preferredDarkTheme, forKey: "preferredDarkTheme") }
    }

    @Published var manualTheme: String {
        didSet { UserDefaults.standard.set(manualTheme, forKey: "manualTheme") }
    }

    init() {
        self.useSystemTheme = UserDefaults.standard.object(forKey: "useSystemTheme") as? Bool ?? true
        self.preferredLightTheme = UserDefaults.standard.string(forKey: "preferredLightTheme") ?? "light-classic"
        self.preferredDarkTheme = UserDefaults.standard.string(forKey: "preferredDarkTheme") ?? "dark-charcoal"
        self.manualTheme = UserDefaults.standard.string(forKey: "manualTheme") ?? "light-classic"
    }

    // MARK: Computed properties

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
