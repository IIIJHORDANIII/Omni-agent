import SwiftUI

struct IntelligenceGlow: View {
    let isActive: Bool
    let intensity: CGFloat
    
    @State private var rotation: Double = 0
    @State private var pulseScale: CGFloat = 1.0
    
    var body: some View {
        ZStack {
            // Layer 1: Outer soft glow (largest, most blurred)
            Circle()
                .stroke(
                    AngularGradient(
                        gradient: Gradient(colors: [
                            .blue.opacity(0.0),
                            .blue.opacity(0.3 * intensity),
                            .purple.opacity(0.4 * intensity),
                            .cyan.opacity(0.3 * intensity),
                            .blue.opacity(0.0)
                        ]),
                        center: .center,
                        startAngle: .degrees(rotation),
                        endAngle: .degrees(rotation + 360)
                    ),
                    lineWidth: 15
                )
                .blur(radius: 12)
                .scaleEffect(pulseScale)
                .opacity(isActive ? 0.6 : 0)
            
            // Layer 2: Medium glow
            Circle()
                .stroke(
                    AngularGradient(
                        gradient: Gradient(colors: [
                            .cyan.opacity(0.0),
                            .blue.opacity(0.5 * intensity),
                            .white.opacity(0.3 * intensity),
                            .purple.opacity(0.4 * intensity),
                            .cyan.opacity(0.0)
                        ]),
                        center: .center,
                        startAngle: .degrees(rotation + 45),
                        endAngle: .degrees(rotation + 405)
                    ),
                    lineWidth: 8
                )
                .blur(radius: 6)
                .scaleEffect(pulseScale * 0.98)
                .opacity(isActive ? 0.8 : 0)
            
            // Layer 3: Inner sharp line (crisp)
            Circle()
                .stroke(
                    AngularGradient(
                        gradient: Gradient(colors: [
                            .white.opacity(0.0),
                            .blue.opacity(0.8 * intensity),
                            .cyan.opacity(0.9 * intensity),
                            .white.opacity(0.7 * intensity),
                            .blue.opacity(0.8 * intensity),
                            .white.opacity(0.0)
                        ]),
                        center: .center,
                        startAngle: .degrees(rotation + 90),
                        endAngle: .degrees(rotation + 450)
                    ),
                    lineWidth: 2
                )
                .blur(radius: 1)
                .opacity(isActive ? 1.0 : 0)
        }
        .onAppear {
            guard isActive else { return }
            startAnimations()
        }
        .onChange(of: isActive) { _, active in
            if active {
                startAnimations()
            }
        }
    }
    
    private func startAnimations() {
        // Rotation animation
        withAnimation(
            .linear(duration: 2.0)
            .repeatForever(autoreverses: false)
        ) {
            rotation = 360
        }
        
        // Pulse animation
        withAnimation(
            .easeInOut(duration: 1.5)
            .repeatForever(autoreverses: true)
        ) {
            pulseScale = 1.02
        }
    }
}
