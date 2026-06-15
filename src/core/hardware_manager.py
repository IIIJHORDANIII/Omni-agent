from core.execution_service import ExecutionService

class HardwareManager:
    @staticmethod
    def set_volume(level: int):
        """Define volume (0-100)."""
        level = max(0, min(100, level))
        return ExecutionService.send_command_to_swift({"action": "set_volume", "level": level})

    @staticmethod
    def set_brightness(level: int):
        """Define brilho (0-100)."""
        level = max(0, min(100, level))
        return ExecutionService.send_command_to_swift({"action": "set_brightness", "level": level})

    @staticmethod
    def set_input_volume(level: int):
        """Define o volume do microfone (0-100)."""
        level = max(0, min(100, level))
        script = f"set volume input volume {level}"
        return ExecutionService.run_applescript(script)

    @staticmethod
    def set_internal_mic_as_default():
        """Força o microfone interno como dispositivo de entrada padrão."""
        # Tenta via SwitchAudioSource (mais confiável que UI Scripting)
        result = ExecutionService.run_terminal_command("SwitchAudioSource -t input -s 'Built-in Microphone' 2>/dev/null")
        if result.get("exit_code") == 0:
            return "Microfone interno definido como padrão."
        
        # Fallback: AppleScript genérico para selecionar o primeiro dispositivo de entrada
        script = '''
        tell application "System Events"
            tell process "CoreServicesUIAgent"
                try
                    click menu bar item "Sound" of menu bar 1
                end try
            end tell
        end tell
        '''
        ExecutionService.run_applescript(script)
        return "Tentativa de seleção de microfone via System Events."

    @staticmethod
    def toggle_mute():
        """Alterna mudo."""
        return ExecutionService.send_command_to_swift({"action": "toggle_mute"})
