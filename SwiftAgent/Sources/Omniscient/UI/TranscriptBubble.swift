import SwiftUI

struct TranscriptBubble: View {
    let text: String
    let isUser: Bool
    let isTyping: Bool
    
    @State private var displayedText: String = ""
    @State private var typewriterTask: Task<Void, Never>?
    
    var body: some View {
        VStack(spacing: 12) {
            // Icon/Avatar
            HStack {
                if isUser {
                    Spacer()
                }
                
                if !isUser {
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 16))
                        .foregroundColor(.cyan)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color.cyan.opacity(0.2))
                        )
                }
                
                VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {
                    Text(isUser ? "Você" : "Omni")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                    
                    Text(displayedText)
                        .font(.system(size: isUser ? 18 : 20, weight: isUser ? .regular : .light))
                        .foregroundColor(.white)
                        .multilineTextAlignment(isUser ? .trailing : .leading)
                        .frame(maxWidth: 500, alignment: isUser ? .trailing : .leading)
                }
                
                if !isUser {
                    Spacer()
                }
            }
            .padding(.horizontal, 40)
            
            // Typing indicator
            if isTyping && displayedText.isEmpty {
                TypingIndicator()
                    .padding(.leading, isUser ? 0 : 44)
            }
        }
        .onChange(of: text) { _, newValue in
            startTypewriter(newValue)
        }
        .onAppear {
            if !text.isEmpty {
                startTypewriter(text)
            }
        }
        .onDisappear {
            typewriterTask?.cancel()
        }
    }
    
    private func startTypewriter(_ fullText: String) {
        typewriterTask?.cancel()
        displayedText = ""
        
        guard !fullText.isEmpty else { return }
        
        let chars = Array(fullText)
        var index = 0
        
        typewriterTask = Task {
            while index < chars.count && !Task.isCancelled {
                displayedText += String(chars[index])
                index += 1
                
                // Adaptive speed: faster for spaces/punctuation, slower for letters
                let char = chars[index - 1]
                let delay: UInt64 = char == " " ? 20_000_000 :
                    (char.isPunctuation ? 80_000_000 : 30_000_000)
                
                try? await Task.sleep(nanoseconds: delay)
            }
        }
    }
}

struct TypingIndicator: View {
    @State private var dotOffsets: [CGFloat] = [0, 0, 0]
    
    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(Color.cyan.opacity(0.6))
                    .frame(width: 6, height: 6)
                    .offset(y: dotOffsets[index])
            }
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 0.4).repeatForever()) {
                dotOffsets[0] = -5
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                withAnimation(.easeInOut(duration: 0.4).repeatForever()) {
                    dotOffsets[1] = -5
                }
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                withAnimation(.easeInOut(duration: 0.4).repeatForever()) {
                    dotOffsets[2] = -5
                }
            }
        }
    }
}
