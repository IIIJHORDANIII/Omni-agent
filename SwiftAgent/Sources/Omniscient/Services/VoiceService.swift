import Foundation
import AVFoundation
import Speech

class VoiceService: NSObject, ObservableObject, @unchecked Sendable {
    private let synthesizer = AVSpeechSynthesizer()
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "pt-BR"))
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()
    
    @MainActor @Published var isListening = false
    @MainActor @Published var transcribedText = ""
    
    func speak(_ text: String) {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        
        let utterance = AVSpeechUtterance(string: text)
        
        // Prioridade: Antônio (Premium), Alex (Premium), Fallback PT-BR
        let voices = AVSpeechSynthesisVoice.speechVoices()
        if let premium = voices.first(where: { $0.name.contains("Antonio") || $0.name.contains("Antônio") }) {
            utterance.voice = premium
        } else if let alex = voices.first(where: { $0.name.contains("Alex") }) {
            utterance.voice = alex
        } else {
            utterance.voice = AVSpeechSynthesisVoice(language: "pt-BR")
        }
        
        utterance.rate = 0.52 
        utterance.pitchMultiplier = 1.0
        utterance.volume = 1.0
        
        synthesizer.speak(utterance)
    }
    
    func startListening() throws {
        recognitionTask?.cancel()
        recognitionTask = nil
        
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.removeTap(onBus: 0)
        
        let request = SFSpeechAudioBufferRecognitionRequest()
        self.recognitionRequest = request
        request.shouldReportPartialResults = true
        request.requiresOnDeviceRecognition = true
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            request.append(buffer)
        }
        
        audioEngine.prepare()
        try audioEngine.start()
        
        Task { @MainActor in
            self.isListening = true
            self.transcribedText = ""
        }
        
        recognitionTask = speechRecognizer?.recognitionTask(with: request) { [weak self] result, error in
            if let result = result {
                let text = result.bestTranscription.formattedString
                Task { @MainActor in
                    self?.transcribedText = text
                }
            }
            if error != nil || result?.isFinal == true {
                self?.stopListening()
            }
        }
    }
    
    func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        Task { @MainActor in
            self.isListening = false
        }
    }
}
