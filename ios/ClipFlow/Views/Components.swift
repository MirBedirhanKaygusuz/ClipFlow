import SwiftUI

// MARK: - Reusable UI Components

struct GlassyCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding()
            .background(.ultraThinMaterial)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Theme.surface.opacity(0.8))
            )
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Theme.borderGradient, lineWidth: 1)
            )
            .shadow(color: Theme.neonPurple.opacity(0.1), radius: 10, x: 0, y: 5)
    }
}

struct NeonButtonStyle: ButtonStyle {
    var isGlowing: Bool = true

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.bold())
            .padding()
            .frame(maxWidth: .infinity)
            .background(Theme.primaryGradient)
            .foregroundColor(.white)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: configuration.isPressed)
            .shadow(
                color: isGlowing ? Theme.neonPurple.opacity(0.4) : .clear,
                radius: 12, x: 0, y: 0
            )
    }
}

struct NeonBorderButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .padding()
            .frame(maxWidth: .infinity)
            .background(.ultraThinMaterial)
            .foregroundColor(.white)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(Theme.primaryGradient, lineWidth: 1.5)
            )
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.spring(), value: configuration.isPressed)
    }
}

struct NeonProgressView: View {
    let progress: Double

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Theme.surface)
                    .frame(height: 8)

                RoundedRectangle(cornerRadius: 8)
                    .fill(Theme.primaryGradient)
                    .frame(width: max(0, geometry.size.width * CGFloat(progress)), height: 8)
                    .shadow(color: Theme.neonTeal.opacity(0.6), radius: 6, x: 0, y: 0)
                    .animation(.easeInOut(duration: 0.3), value: progress)
            }
        }
        .frame(height: 8)
    }
}
