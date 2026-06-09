import Foundation
import ScreenCaptureKit
import Vision
import CoreImage

@MainActor
class VisionService {
    static let shared = VisionService()
    
    private init() {}
    
    func captureScreen() async throws -> CGImage? {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        guard let display = content.displays.first else { return nil }
        
        let filter = SCContentFilter(display: display, excludingWindows: [])
        let config = SCStreamConfiguration()
        config.width = display.width
        config.height = display.height
        
        // Captura um frame único
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        return image
    }
    
    func analyzeImage(image: CGImage) async throws -> String {
        return try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                
                let observations = request.results as? [VNRecognizedTextObservation] ?? []
                let recognizedText = observations.compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
                continuation.resume(returning: recognizedText)
            }
            
            request.recognitionLevel = .accurate
            
            let handler = VNImageRequestHandler(cgImage: image, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }
}
