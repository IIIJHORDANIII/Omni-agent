import SwiftUI
import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
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
        
        // Mantém o app rodando (sem isso o SwiftUI fecha sozinho)
        NSApplication.shared.run()
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
