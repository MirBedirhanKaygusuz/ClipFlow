import SwiftUI

// MARK: - Theme (Digital Darkroom)

/// Defines the color palette and constants for the Digital Darkroom design system.
enum Theme {
    /// Pure dark navy / off-black background.
    static let background = Color(red: 0.06, green: 0.07, blue: 0.10)
    
    /// Elevated surface color (for solid card backgrounds without blur).
    static let surface = Color(red: 0.12, green: 0.13, blue: 0.18)
    
    /// Neon Teal accent.
    static let neonTeal = Color(red: 0.28, green: 0.75, blue: 0.89) // #48BFE3
    
    /// Neon Purple accent.
    static let neonPurple = Color(red: 0.62, green: 0.31, blue: 0.87) // #9D4EDD
    
    /// Main primary gradient.
    static let primaryGradient = LinearGradient(
        colors: [neonPurple, neonTeal],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    
    /// Accent gradient for subtle borders or active states.
    static let borderGradient = LinearGradient(
        colors: [neonPurple.opacity(0.6), neonTeal.opacity(0.6)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    
    /// Subdued text color for secondary information.
    static let textSecondary = Color(white: 0.7)
}
