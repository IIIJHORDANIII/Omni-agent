from core.execution_service import ExecutionService

class HardwareManager:
    @staticmethod
    def set_volume(level: int):
        """Define volume (0-100)."""
        return ExecutionService.send_command_to_swift({"action": "set_volume", "level": level})

    @staticmethod
    def set_brightness(level: int):
        """Define brilho (0-100)."""
        return ExecutionService.send_command_to_swift({"action": "set_brightness", "level": level})

    @staticmethod
    def set_input_volume(level: int):
        """Define o volume do microfone (0-100)."""
        script = f"set volume input volume {level}"
        return ExecutionService.run_applescript(script)

    @staticmethod
    def set_internal_mic_as_default():
        """Força o microfone interno como dispositivo de entrada padrão."""
        # Tenta via AppleScript buscando pelo nome padrão do sistema em PT e EN
        script = '''
        tell application "System Preferences" to reveal anchor "input" of pane id "com.apple.preference.sound"
        tell application "System Events" to tell process "System Settings"
            try
                -- Tenta encontrar o microfone interno na lista
                set internalMicNames to {"Microfone Interno", "Internal Microphone", "MacBook Pro Microphone", "MacBook Air Microphone"}
                repeat with micName in internalMicNames
                    try
                        select (row 1 of table 1 of scroll area 1 of group 1 of group 2 of group 1 of group 1 of window 1 whose value of static text 1 is micName)
                        return "Microfone " & micName & " selecionado."
                    end try
                end repeat
            end try
        end tell
        '''
        # Como o System Settings mudou muito no Ventura/Sonoma, o comando de volume 
        # costuma ser o mais garantido para a entrada atual.
        # Vamos usar um comando shell mais direto que o AppleScript de UI se possível.
        return ExecutionService.run_terminal_command("SwitchAudioSource -t input -s 'Built-in Microphone' || true")

    @staticmethod
    def toggle_mute():
        """Alterna mudo."""
        return ExecutionService.send_command_to_swift({"action": "toggle_mute"})
