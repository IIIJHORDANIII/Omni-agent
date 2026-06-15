import SwiftUI
import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
    private var keepAliveTimer: Timer?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Define como app de segundo plano (não aparece no dock)
        NSApplication.shared.setActivationPolicy(.accessory)
        
        // Inicia o serviço de escuta de comandos
        CommandListenerService.shared.start()
        
        // Pré-inicializa o overlay Siri
        Task { @MainActor in
            _ = SiriOverlayController.shared
        }
        
        print("Omniscient Headless Executor iniciado.")
        
        // Mantém o app rodando via timer infinito (mais seguro que NSApp.run())
        keepAliveTimer = Timer.scheduledTimer(withTimeInterval: 60.0, repeats: true) { _ in
            // Apenas mantém o RunLoop ativo
        }
        RunLoop.current.add(keepAliveTimer!, forMode: .default)
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        keepAliveTimer?.invalidate()
    }
}

@main
struct OmniscientApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}
