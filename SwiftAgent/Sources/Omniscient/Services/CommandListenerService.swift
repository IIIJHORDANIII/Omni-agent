import Foundation
import ApplicationServices
import AppKit
import CoreAudio
import CoreGraphics
import IOKit

@MainActor
class CommandListenerService {
    static let shared = CommandListenerService()
    
    private let socketPath = "/tmp/omniscient_agent.sock"
    private nonisolated(unsafe) var isRunning = false
    
    // Para cálculo de CPU (delta entre amostras)
    private nonisolated(unsafe) var lastCPULoad: host_cpu_load_info?

    func start() {
        guard !isRunning else { return }
        isRunning = true
        
        try? FileManager.default.removeItem(atPath: socketPath)
        
        // Iniciar Monitor de Eventos Globais
        NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { event in
            let flags = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
            let keyCode = event.keyCode
            
            // LOG DE DEPURAÇÃO TOTAL: Imprime absolutamente qualquer tecla pressionada enquanto o app roda em background
            print("DEBUG SWIFT: KeyCode: \(keyCode), Flags: \(flags)")
            
            // Atalho para Chat: Command + Shift + O (KeyCode 31)
            if flags.contains([.command, .shift]) && keyCode == 31 {
                print("DEBUG SWIFT: Hotkey Chat Detectada (Cmd+Shift+O)!")
                self.notifyPython(event: "hotkey_chat")
            }
            
            // Atalho para Voz: Command + Shift + Enter (KeyCode 36)
            if flags.contains([.command, .shift]) && keyCode == 36 {
                print("DEBUG SWIFT: Hotkey Voz Detectada (Cmd+Shift+Enter)!")
                self.notifyPython(event: "hotkey_voice")
            }
        }
        
        DispatchQueue.global(qos: .background).async {
            self.runSocketServer()
        }
    }
    
    private nonisolated(unsafe) var eventQueue: [String] = []
    private let queueLock = NSLock()

    private func notifyPython(event: String) {
        queueLock.lock()
        eventQueue.append(event)
        queueLock.unlock()
        print("DEBUG: Hotkey detectada: \(event)")
    }
    
    private nonisolated func getEventsSync() -> [String: Any] {
        queueLock.lock()
        let events = eventQueue
        eventQueue.removeAll()
        queueLock.unlock()
        return ["status": "ok", "events": events]
    }

    private nonisolated func runSocketServer() {
        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd != -1 else { return }
        
        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        
        let path = socketPath
        let pathBytes = Array(path.utf8)

        withUnsafeMutableBytes(of: &addr.sun_path) { ptr in
            let dest = ptr.baseAddress!.assumingMemoryBound(to: Int8.self)
            let len = min(pathBytes.count, ptr.count - 1)
            for i in 0..<len { dest[i] = Int8(pathBytes[i]) }
            dest[len] = 0
        }

        let addrPtr = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { $0 }
        }
        
        guard bind(fd, addrPtr, socklen_t(MemoryLayout<sockaddr_un>.size)) == 0 else { return }
        guard listen(fd, 5) == 0 else { return }
        
        while isRunning {
            let clientFd = accept(fd, nil, nil)
            if clientFd != -1 {
                handleConnection(clientFd)
                close(clientFd)
            }
        }
    }
    
    private nonisolated func handleConnection(_ clientFd: Int32) {
        var buffer = [UInt8](repeating: 0, count: 4096)
        let bytesRead = read(clientFd, &buffer, buffer.count)
        if bytesRead > 0 {
            if let commandData = String(bytes: buffer[0..<bytesRead], encoding: .utf8)?.data(using: .utf8) {
                if let json = try? JSONSerialization.jsonObject(with: commandData) as? [String: Any] {
                    let response = self.executeCommand(json)
                    if let responseData = try? JSONSerialization.data(withJSONObject: response) {
                        responseData.withUnsafeBytes { ptr in
                            _ = write(clientFd, ptr.baseAddress, responseData.count)
                        }
                    }
                }
            }
        }
    }
    
    private nonisolated func executeCommand(_ command: [String: Any]) -> [String: Any] {
        guard let action = command["action"] as? String else { return ["status": "error"] }
        
        var sendableCommand: [String: String] = [:]
        for (key, value) in command { sendableCommand[key] = String(describing: value) }
        
        if action == "get_status" {
            return self.getSystemStatusSync()
        } else if action == "get_active_app" {
            return self.getActiveAppSync()
        } else if action == "get_events" {
            return self.getEventsSync()
        } else if action == "analyze_screen" {
            // Usamos uma classe auxiliar thread-safe para capturar o resultado
            class AnalysisBox: @unchecked Sendable {
                var text: String?
            }
            let box = AnalysisBox()
            let semaphore = DispatchSemaphore(value: 0)
            
            Task { @MainActor in
                if let image = try? await VisionService.shared.captureScreen() {
                    if let text = try? await VisionService.shared.analyzeImage(image: image) {
                        box.text = text
                    }
                }
                semaphore.signal()
            }
            
            _ = semaphore.wait(timeout: .now() + 5.0)
            if let resultText = box.text {
                return ["status": "ok", "action": "analyze_screen", "text": resultText]
            }
            return ["status": "error", "text": "Falha na análise ou timeout"]
        }

        
        Task { @MainActor in
            switch action {
            case "move_window":
                if let appName = sendableCommand["app"],
                   let x = Double(sendableCommand["x"] ?? ""), let y = Double(sendableCommand["y"] ?? ""),
                   let w = Double(sendableCommand["w"] ?? ""), let h = Double(sendableCommand["h"] ?? "") {
                    self.moveWindow(appName: appName, x: CGFloat(x), y: CGFloat(y), w: CGFloat(w), h: CGFloat(h))
                }
            case "click_at":
                if let x = Double(sendableCommand["x"] ?? ""), let y = Double(sendableCommand["y"] ?? "") {
                    self.clickAt(x: CGFloat(x), y: CGFloat(y))
                }
            case "type_text":
                if let text = sendableCommand["text"] { self.typeText(text: text) }
            case "press_key":
                if let keyName = sendableCommand["key"] { self.pressKeyByName(keyName: keyName) }
            case "scroll":
                if let amount = Int32(sendableCommand["amount"] ?? "") { self.scroll(amount: amount) }
            case "close_app":
                if let appName = sendableCommand["app"] { self.closeApp(appName: appName) }
            case "terminate_pid":
                if let pidStr = sendableCommand["pid"], let pid = Int32(pidStr) { self.terminatePid(pid: pid) }
            case "bring_to_front":
                if let appName = sendableCommand["app"] { self.bringToFront(appName: appName) }
            case "set_volume":
                if let level = Float(sendableCommand["level"] ?? "") { self.setVolume(level: level / 100.0) }
            case "set_brightness":
                if let level = Float(sendableCommand["level"] ?? "") { self.setBrightness(level: level / 100.0) }
            case "toggle_mute":
                self.toggleMute()
            case "overlay_show":
                Task { @MainActor in
                    SiriOverlayController.shared.show()
                }
            case "overlay_hide":
                Task { @MainActor in
                    SiriOverlayController.shared.hide()
                }
            case "overlay_transcript":
                if let text = sendableCommand["text"] {
                    Task { @MainActor in
                        SiriOverlayController.shared.updateTranscript(text)
                    }
                }
            case "overlay_response":
                if let text = sendableCommand["text"] {
                    Task { @MainActor in
                        SiriOverlayController.shared.updateResponse(text)
                    }
                }
            case "overlay_error":
                if let text = sendableCommand["text"] {
                    Task { @MainActor in
                        SiriOverlayController.shared.setError(text)
                    }
                }
            default: break
            }
        }
        return ["status": "queued"]
    }
    
    private func setVolume(level: Float) {
        var deviceID = AudioObjectID(kAudioObjectUnknown)
        var size = UInt32(MemoryLayout<AudioObjectID>.size)
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain)
        
        AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &propertyAddress, 0, nil, &size, &deviceID)
        
        propertyAddress.mSelector = kAudioDevicePropertyVolumeScalar
        propertyAddress.mScope = kAudioDevicePropertyScopeOutput
        
        var vol = level
        AudioObjectSetPropertyData(deviceID, &propertyAddress, 0, nil, UInt32(MemoryLayout<Float>.size), &vol)
    }
    
    private func setBrightness(level: Float) {
        let display = CGMainDisplayID()
        let brightness = max(0.0, min(1.0, level))
        CGSetDisplayTransferByTable(display, 256, [brightness], [brightness], [brightness])
    }
    
    private func toggleMute() {
        var deviceID = AudioObjectID(kAudioObjectUnknown)
        var size = UInt32(MemoryLayout<AudioObjectID>.size)
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain)
        
        AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &propertyAddress, 0, nil, &size, &deviceID)
        
        propertyAddress.mSelector = kAudioDevicePropertyMute
        propertyAddress.mScope = kAudioDevicePropertyScopeOutput
        
        var isMuted: UInt32 = 0
        var sizeMute = UInt32(MemoryLayout<UInt32>.size)
        AudioObjectGetPropertyData(deviceID, &propertyAddress, 0, nil, &sizeMute, &isMuted)
        
        isMuted = isMuted == 0 ? 1 : 0
        AudioObjectSetPropertyData(deviceID, &propertyAddress, 0, nil, UInt32(MemoryLayout<UInt32>.size), &isMuted)
    }

    private func clickAt(x: CGFloat, y: CGFloat) {
        let point = CGPoint(x: x, y: y)
        if let mouseEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left) { mouseEvent.post(tap: .cghidEventTap) }
        if let releaseEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left) { releaseEvent.post(tap: .cghidEventTap) }
    }
    
    private func typeText(text: String) {
        for char in text.utf16 {
            if let event = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: true) {
                event.keyboardSetUnicodeString(stringLength: 1, unicodeString: [char])
                event.post(tap: .cghidEventTap)
            }
            if let event = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: false) {
                event.keyboardSetUnicodeString(stringLength: 1, unicodeString: [char])
                event.post(tap: .cghidEventTap)
            }
        }
    }

    private func pressKeyByName(keyName: String) {
        let mapping: [String: UInt16] = [
            "enter": 36, "return": 36, "tab": 48, "space": 49, "delete": 51, "escape": 53,
            "up": 126, "down": 125, "left": 123, "right": 124
        ]
        if let code = mapping[keyName.lowercased()] {
            if let down = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: true) { down.post(tap: .cghidEventTap) }
            if let up = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: false) { up.post(tap: .cghidEventTap) }
        }
    }

    private func scroll(amount: Int32) {
        if let event = CGEvent(scrollWheelEvent2Source: nil, units: .line, wheelCount: 1, wheel1: amount, wheel2: 0, wheel3: 0) {
            event.post(tap: CGEventTapLocation.cghidEventTap)
        }
    }

    private nonisolated func getSystemStatusSync() -> [String: Any] {
        let apps = NSWorkspace.shared.runningApplications
        let appNames = apps.compactMap { $0.bundleIdentifier }
        
        let response: [String: Any] = [
            "status": "ok",
            "running_apps": appNames,
            "cpu": self.getCPUUsagePercentage(),
            "memory": self.getMemoryStats(),
            "battery": self.getBatteryInfo()
        ]
        
        return response
    }
    
    private nonisolated func getCPUUsagePercentage() -> Double {
        var cpuLoad = host_cpu_load_info()
        let HOST_CPU_LOAD_INFO_COUNT = mach_msg_type_number_t(MemoryLayout<host_cpu_load_info_data_t>.size / MemoryLayout<integer_t>.size)
        var count = HOST_CPU_LOAD_INFO_COUNT
        
        let result = withUnsafeMutablePointer(to: &cpuLoad) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO, $0, &count)
            }
        }
        
        guard result == KERN_SUCCESS else { return 0.0 }
        
        var percentage = 0.0
        if let last = self.lastCPULoad {
            let userDiff = Double(cpuLoad.cpu_ticks.0 - last.cpu_ticks.0)
            let sysDiff = Double(cpuLoad.cpu_ticks.1 - last.cpu_ticks.1)
            let idleDiff = Double(cpuLoad.cpu_ticks.2 - last.cpu_ticks.2)
            let niceDiff = Double(cpuLoad.cpu_ticks.3 - last.cpu_ticks.3)
            
            let totalDiff = userDiff + sysDiff + idleDiff + niceDiff
            if totalDiff > 0 {
                percentage = (userDiff + sysDiff + niceDiff) / totalDiff * 100.0
            }
        }
        
        self.lastCPULoad = cpuLoad
        return percentage
    }
    
    private nonisolated func getMemoryStats() -> [String: Any] {
        var stats = vm_statistics64()
        var count = mach_msg_type_number_t(MemoryLayout<vm_statistics64_data_t>.size / MemoryLayout<integer_t>.size)
        
        let result = withUnsafeMutablePointer(to: &stats) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                host_statistics64(mach_host_self(), HOST_VM_INFO64, $0, &count)
            }
        }
        
        guard result == KERN_SUCCESS else { return [:] }
        
        let pageSize = UInt64(getpagesize())
        let free = UInt64(stats.free_count) * pageSize
        let active = UInt64(stats.active_count) * pageSize
        let inactive = UInt64(stats.inactive_count) * pageSize
        let wired = UInt64(stats.wire_count) * pageSize
        let compressed = UInt64(stats.compressor_page_count) * pageSize
        
        let used = active + wired + compressed
        let total = ProcessInfo.processInfo.physicalMemory
        
        return [
            "total_gb": Double(total) / 1024 / 1024 / 1024,
            "used_gb": Double(used) / 1024 / 1024 / 1024,
            "free_gb": Double(free + inactive) / 1024 / 1024 / 1024,
            "usage_percent": Double(used) / Double(total) * 100.0
        ]
    }
    
    private nonisolated func getBatteryInfo() -> [String: Any] {
        let matching = IOServiceMatching("AppleSmartBattery")
        let service = IOServiceGetMatchingService(kIOMainPortDefault, matching)
        if service == 0 { return [:] }
        defer { IOObjectRelease(service) }
        
        var properties: Unmanaged<CFMutableDictionary>?
        let result = IORegistryEntryCreateCFProperties(service, &properties, kCFAllocatorDefault, 0)
        if result != KERN_SUCCESS || properties == nil { return [:] }
        
        let dict = properties!.takeRetainedValue() as? [String: Any] ?? [:]
        
        let capacity = dict["CurrentCapacity"] as? Int ?? 0
        let maxCapacity = dict["MaxCapacity"] as? Int ?? 100
        let isCharging = dict["IsCharging"] as? Bool ?? false
        let percentage = Double(capacity) / Double(maxCapacity) * 100.0
        
        return [
            "percentage": Int(percentage),
            "is_charging": isCharging,
            "capacity": capacity,
            "max_capacity": maxCapacity
        ]
    }
    
    private nonisolated func getActiveAppSync() -> [String: Any] {
        let app = NSWorkspace.shared.frontmostApplication
        let bundleId = app?.bundleIdentifier ?? "unknown"
        
        // Tentar obter o título da janela ativa para contexto de projeto
        var windowTitle = "unknown"
        if let pid = app?.processIdentifier {
            let appElement = AXUIElementCreateApplication(pid)
            var focusedWindow: CFTypeRef?
            if AXUIElementCopyAttributeValue(appElement, kAXFocusedWindowAttribute as CFString, &focusedWindow) == .success {
                let window = focusedWindow as! AXUIElement
                var title: CFTypeRef?
                if AXUIElementCopyAttributeValue(window, kAXTitleAttribute as CFString, &title) == .success {
                    windowTitle = title as? String ?? "unknown"
                }
            }
        }
        
        return ["status": "ok", "active_app": bundleId, "window_title": windowTitle]
    }
    
    private nonisolated func getSelectedTextSync() -> [String: Any] {
        let app = NSWorkspace.shared.frontmostApplication
        guard let pid = app?.processIdentifier else { return ["status": "error", "message": "No active app"] }
        
        let appElement = AXUIElementCreateApplication(pid)
        var focusedElement: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(appElement, kAXFocusedUIElementAttribute as CFString, &focusedElement)
        
        if result == .success {
            let element = focusedElement as! AXUIElement
            var selectedText: CFTypeRef?
            let textResult = AXUIElementCopyAttributeValue(element, kAXSelectedTextAttribute as CFString, &selectedText)
            
            if textResult == .success {
                let text = selectedText as? String ?? ""
                return ["status": "ok", "selected_text": text]
            }
        }
        
        return ["status": "error", "message": "Could not get selected text"]
    }

    private func closeApp(appName: String) {
        let apps = NSRunningApplication.runningApplications(withBundleIdentifier: appName)
        apps.forEach { $0.terminate() }
    }

    private func terminatePid(pid: Int32) {
        if let app = NSRunningApplication(processIdentifier: pid) {
            app.forceTerminate()
        }
    }

    private func bringToFront(appName: String) {
        let apps = NSRunningApplication.runningApplications(withBundleIdentifier: appName)
        apps.first?.activate()
    }

    private func moveWindow(appName: String, x: CGFloat, y: CGFloat, w: CGFloat, h: CGFloat) {
        let apps = NSRunningApplication.runningApplications(withBundleIdentifier: appName)
        guard let app = apps.first else { return }
        
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(appElement, kAXWindowsAttribute as CFString, &value)
        
        guard result == .success, let windows = value as? [AXUIElement], let window = windows.first else { return }
        
        var pos = CGPoint(x: x, y: y)
        if let posRef = AXValueCreate(.cgPoint, &pos) { AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, posRef) }
        
        var size = CGSize(width: w, height: h)
        if let sizeRef = AXValueCreate(.cgSize, &size) { AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, sizeRef) }
    }
}
