import SwiftUI
import AppKit

@MainActor
class SiriOverlayController {
    static let shared = SiriOverlayController()
    
    private var panel: NSPanel?
    private var overlayView: SiriOverlayView?
    private var hideTimer: Timer?
    
    private init() {}
    
    var isVisible: Bool {
        panel?.isVisible ?? false
    }
    
    func show() {
        if panel == nil {
            createPanel()
        }
        
        hideTimer?.invalidate()
        hideTimer = nil
        
        overlayView?.show()
        panel?.orderFront(nil)
    }
    
    func hide() {
        overlayView?.hide()
        
        hideTimer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: false) { [weak self] _ in
            Task { @MainActor in
                self?.panel?.orderOut(nil)
            }
        }
    }
    
    func updateTranscript(_ text: String) {
        overlayView?.updateTranscript(text)
    }
    
    func updateResponse(_ text: String) {
        overlayView?.updateResponse(text)
    }
    
    func setError(_ message: String) {
        overlayView?.setError(message)
    }
    
    private func createPanel() {
        let screen = NSScreen.main ?? NSScreen.screens[0]
        let rect = screen.frame
        
        panel = NSPanel(
            contentRect: rect,
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        
        panel?.level = .screenSaver
        panel?.isOpaque = false
        panel?.backgroundColor = .clear
        panel?.hasShadow = false
        panel?.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        panel?.isMovableByWindowBackground = false
        panel?.hidesOnDeactivate = false
        
        overlayView = SiriOverlayView(onDismiss: { [weak self] in
            self?.hide()
        })
        
        panel?.contentView = NSHostingView(rootView: overlayView)
        panel?.setFrame(rect, display: true)
    }
}

struct SiriOverlayView: View {
    let onDismiss: () -> Void
    
    @State private var isShowing = false
    @State private var showGlow = false
    @State private var showTranscript = false
    @State private var showResponse = false
    
    @State private var transcript: String = ""
    @State private var response: String = ""
    @State private var isError = false
    
    @State private var dismissTask: Task<Void, Never>?
    
    var body: some View {
        ZStack {
            // Background dimming
            Color.black.opacity(isShowing ? 0.7 : 0.0)
                .ignoresSafeArea()
                .onTapGesture {
                    onDismiss()
                }
            
            VStack {
                Spacer()
                
                // Main content area
                VStack(spacing: 30) {
                    // Glow circle with status
                    ZStack {
                        // Glow effect
                        IntelligenceGlow(isActive: showGlow, intensity: 1.0)
                            .frame(width: 280, height: 280)
                        
                        // Center orb
                        Circle()
                            .fill(
                                RadialGradient(
                                    gradient: Gradient(colors: [
                                        .cyan.opacity(0.8),
                                        .blue.opacity(0.6),
                                        .purple.opacity(0.4)
                                    ]),
                                    center: .center,
                                    startRadius: 0,
                                    endRadius: 60
                                )
                            )
                            .frame(width: 100, height: 100)
                            .shadow(color: .cyan.opacity(0.5), radius: 30)
                            .scaleEffect(showGlow ? 1.0 : 0.8)
                            .animation(.easeInOut(duration: 0.5), value: showGlow)
                        
                        // Status text inside orb
                        if response.isEmpty && !isError {
                            Image(systemName: showTranscript ? "waveform" : "mic")
                                .font(.system(size: 32))
                                .foregroundColor(.white)
                                .opacity(showGlow ? 1 : 0)
                        }
                    }
                    .frame(height: 280)
                    
                    // Transcript and Response
                    VStack(spacing: 20) {
                        if showTranscript && !transcript.isEmpty {
                            TranscriptBubble(
                                text: transcript,
                                isUser: true,
                                isTyping: false
                            )
                            .transition(.move(edge: .top).combined(with: .opacity))
                        }
                        
                        if showResponse && !response.isEmpty {
                            TranscriptBubble(
                                text: response,
                                isUser: false,
                                isTyping: true
                            )
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        }
                        
                        if isError && !response.isEmpty {
                            TranscriptBubble(
                                text: response,
                                isUser: false,
                                isTyping: false
                            )
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        }
                    }
                    .padding(.horizontal, 60)
                    
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            }
            .opacity(isShowing ? 1.0 : 0.0)
        }
        .animation(.easeInOut(duration: 0.3), value: isShowing)
    }
    
    func show() {
        transcript = ""
        response = ""
        isError = false
        showTranscript = false
        showResponse = false
        
        withAnimation {
            isShowing = true
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            showGlow = true
        }
    }
    
    func hide() {
        withAnimation {
            showGlow = false
            isShowing = false
        }
        
        showTranscript = false
        showResponse = false
    }
    
    func updateTranscript(_ text: String) {
        transcript = text
        withAnimation {
            showTranscript = true
        }
    }
    
    func updateResponse(_ text: String) {
        response = text
        isError = false
        withAnimation {
            showResponse = true
            showTranscript = false
        }
    }
    
    func setError(_ message: String) {
        response = message
        isError = true
        withAnimation {
            showResponse = true
        }
    }
}
