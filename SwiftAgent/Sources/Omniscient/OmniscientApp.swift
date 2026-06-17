import SwiftUI
import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
    private var hiddenWindow: NSWindow?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApplication.shared.setActivationPolicy(.accessory)
        
        CommandListenerService.shared.start()
        
        Task { @MainActor in
            _ = SiriOverlayController.shared
        }
        
        // Janela oculta mantém o app vivo
        hiddenWindow = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1, height: 1),
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )
        hiddenWindow?.isReleasedWhenClosed = false
        hiddenWindow?.orderBack(nil)
        
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
