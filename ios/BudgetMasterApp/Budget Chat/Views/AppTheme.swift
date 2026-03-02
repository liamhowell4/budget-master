import SwiftUI

// MARK: - App Theme Tokens

enum AppTheme {
    /// Default green accent (#22c55e) used as fallback when no theme is active.
    static let accent: Color = Color(red: 34 / 255, green: 197 / 255, blue: 94 / 255)

    /// Returns the accent color for the given theme scheme, falling back to the default.
    static func accentColor(for scheme: ThemeColorScheme?) -> Color {
        scheme?.accentColor ?? accent
    }

    /// Returns the tint color for the given theme scheme, falling back to the default accent.
    static func tintColor(for scheme: ThemeColorScheme?) -> Color {
        scheme?.tintColor ?? accent
    }

    /// Maps an ExpenseType category ID to a display color
    static func categoryColor(_ id: String) -> Color {
        switch id.uppercased() {
        case "FOOD_OUT":   return Color(red: 249/255, green: 115/255, blue: 22/255)
        case "GROCERIES":  return AppTheme.accent
        case "COFFEE":     return Color(red: 161/255, green: 99/255,  blue: 60/255)
        case "RENT":       return Color(red: 59/255,  green: 130/255, blue: 246/255)
        case "UTILITIES":  return Color(red: 234/255, green: 179/255, blue: 8/255)
        case "MEDICAL":    return Color(red: 239/255, green: 68/255,  blue: 68/255)
        case "GAS":        return Color(red: 168/255, green: 85/255,  blue: 247/255)
        case "RIDE_SHARE": return Color(red: 20/255,  green: 184/255, blue: 166/255)
        case "HOTEL":      return Color(red: 99/255,  green: 102/255, blue: 241/255)
        case "TECH":       return Color(red: 6/255,   green: 182/255, blue: 212/255)
        case "TRAVEL":     return Color(red: 16/255,  green: 185/255, blue: 129/255)
        default:           return Color(uiColor: .systemGray)
        }
    }

    /// Returns the appropriate color for a budget progress bar / stat based on percentage used
    static func budgetProgressColor(_ percentage: Double) -> Color {
        if percentage >= 95 { return .red }
        if percentage >= 50 { return .orange }
        return AppTheme.accent
    }
}

// MARK: - Glass Effect View Modifiers

struct GlassCardModifier: ViewModifier {
    var cornerRadius: CGFloat = 20

    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            content
                .glassEffect(.regular, in: RoundedRectangle(cornerRadius: cornerRadius))
        } else {
            content
                .background(Color(uiColor: .systemBackground))
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
                .shadow(color: .black.opacity(0.06), radius: 10, y: 4)
        }
    }
}

struct GlassInputModifier: ViewModifier {
    var cornerRadius: CGFloat = 24

    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            content
                .glassEffect(.regular, in: RoundedRectangle(cornerRadius: cornerRadius))
        } else {
            content
                .background(Color(uiColor: .secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
        }
    }
}

struct GlassCapsuleModifier: ViewModifier {
    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            content
                .glassEffect(.regular, in: Capsule())
        } else {
            content
                .background(.ultraThinMaterial, in: Capsule())
        }
    }
}

// MARK: - Lucide → SF Symbol Mapping

extension AppTheme {
    /// Maps a Lucide icon name (stored in Firestore categories) to an SF Symbol name.
    static func sfSymbol(for lucideIcon: String) -> String {
        switch lucideIcon.lowercased() {
        case "utensils", "fork", "pizza":           return "fork.knife"
        case "coffee", "cup":                        return "cup.and.saucer.fill"
        case "home", "house":                        return "house.fill"
        case "shopping-cart", "cart", "shopping-bag": return "cart.fill"
        case "laptop", "monitor", "computer":        return "laptopcomputer"
        case "car", "car-taxi-front", "taxi":        return "car.fill"
        case "plane", "airplane":                    return "airplane"
        case "heart-pulse", "activity", "heart":     return "heart.fill"
        case "fuel", "gas-station":                  return "fuelpump.fill"
        case "zap", "bolt", "lightning":             return "bolt.fill"
        case "hotel", "building-2", "building":      return "building.2.fill"
        case "refresh-cw", "repeat":                 return "arrow.clockwise"
        case "more-horizontal", "ellipsis":          return "ellipsis.circle.fill"
        case "music", "headphones":                  return "headphones"
        case "shirt", "shopping-bag-2":              return "bag.fill"
        case "dumbbell", "gym":                      return "dumbbell.fill"
        case "book", "graduation-cap":               return "book.fill"
        case "wifi", "phone":                        return "wifi"
        case "gift":                                 return "gift.fill"
        default:                                     return "creditcard.fill"
        }
    }
}

// MARK: - Environment Keys for Resolved Theme Tokens

// Views read these keys from the environment so the ThemeManager's active
// scheme propagates through the entire tree without ObservableObject
// subscriptions in every leaf view.

private struct AppAccentKey: EnvironmentKey {
    static let defaultValue: Color = AppTheme.accent
}

private struct AppBackgroundTintKey: EnvironmentKey {
    static let defaultValue: Color = .clear
}

private struct AppUserBubbleKey: EnvironmentKey {
    static let defaultValue: Color = .primary
}

private struct AppUserBubbleTextKey: EnvironmentKey {
    static let defaultValue: Color = .white
}

private struct AppAiBubbleKey: EnvironmentKey {
    static let defaultValue: Color = Color(hex: 0xF2F2F7)
}

private struct AppAiBubbleTextKey: EnvironmentKey {
    static let defaultValue: Color = .primary
}

extension EnvironmentValues {
    var appAccent: Color {
        get { self[AppAccentKey.self] }
        set { self[AppAccentKey.self] = newValue }
    }

    var appBackgroundTint: Color {
        get { self[AppBackgroundTintKey.self] }
        set { self[AppBackgroundTintKey.self] = newValue }
    }

    var appUserBubble: Color {
        get { self[AppUserBubbleKey.self] }
        set { self[AppUserBubbleKey.self] = newValue }
    }

    var appUserBubbleText: Color {
        get { self[AppUserBubbleTextKey.self] }
        set { self[AppUserBubbleTextKey.self] = newValue }
    }

    var appAiBubble: Color {
        get { self[AppAiBubbleKey.self] }
        set { self[AppAiBubbleKey.self] = newValue }
    }

    var appAiBubbleText: Color {
        get { self[AppAiBubbleTextKey.self] }
        set { self[AppAiBubbleTextKey.self] = newValue }
    }
}

// MARK: - View Extensions

extension View {
    func glassCard(cornerRadius: CGFloat = 20) -> some View {
        modifier(GlassCardModifier(cornerRadius: cornerRadius))
    }

    func glassInput(cornerRadius: CGFloat = 24) -> some View {
        modifier(GlassInputModifier(cornerRadius: cornerRadius))
    }

    func glassCapsule() -> some View {
        modifier(GlassCapsuleModifier())
    }
}

// MARK: - Keyboard Dismissal

extension View {
    /// Dismisses the keyboard/keypad when the user taps outside a focused field.
    /// Apply to a container view (e.g., the VStack inside a ScrollView body) so
    /// that any tap on non-interactive background area resigns first responder.
    /// SwiftUI buttons handle their own taps before the gesture propagates,
    /// so this does not interfere with any interactive controls.
    func dismissKeyboardOnTap() -> some View {
        self.onTapGesture {
            UIApplication.shared.sendAction(
                #selector(UIResponder.resignFirstResponder),
                to: nil, from: nil, for: nil
            )
        }
    }
}
