import SwiftUI

// MARK: - Theme (Digital Darkroom)

enum Theme {
    static let background = Color(red: 0.06, green: 0.07, blue: 0.10)
    static let surface = Color(red: 0.12, green: 0.13, blue: 0.18)
    static let neonTeal = Color(red: 0.28, green: 0.75, blue: 0.89)
    static let neonPurple = Color(red: 0.62, green: 0.31, blue: 0.87)

    static let primaryGradient = LinearGradient(
        colors: [neonPurple, neonTeal],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let borderGradient = LinearGradient(
        colors: [neonPurple.opacity(0.6), neonTeal.opacity(0.6)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let textSecondary = Color(white: 0.7)
}
