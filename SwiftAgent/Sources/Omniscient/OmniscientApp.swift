import SwiftUI
import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Define como app de segundo plano (não aparece no dock)
        NSApplication.shared.setActivationPolicy(.accessory)
        
        // Inicia o serviço de escuta de comandos
        CommandListenerService.shared.start()
        
        print("Omniscient Headless Executor iniciado.")
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
