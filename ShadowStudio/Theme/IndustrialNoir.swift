import SwiftUI

/// Axiom Ω₁: Industrial Noir 2026 Design System
/// Base: #0A0A0A, Accent: #CCFF00 (Cyber Lime)
public struct Theme {
    public static let background = Color(hex: "0A0A0A")
    public static let surface = Color(hex: "121212")
    public static let surfaceHighlight = Color(hex: "1A1A1A")
    public static let accent = Color(hex: "CCFF00")
    public static let textPrimary = Color.white
    public static let textSecondary = Color(white: 0.6)
    public static let textMuted = Color(white: 0.4)
    public static let danger = Color(hex: "FF3333")
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

struct NeoButtonModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(.body, design: .monospaced).weight(.bold))
            .foregroundColor(Theme.background)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Theme.accent)
            .cornerRadius(4)
            .shadow(color: Theme.accent.opacity(0.3), radius: 5, x: 0, y: 0)
    }
}

extension View {
    func neoButton() -> some View {
        self.modifier(NeoButtonModifier())
    }
}
