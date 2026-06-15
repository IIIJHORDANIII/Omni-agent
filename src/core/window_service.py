import subprocess
from core.execution_service import ExecutionService

class WindowService:
    @staticmethod
    def get_open_windows():
        """Lista janelas abertas via AppleScript."""
        script = '''
        tell application "System Events"
            set windowList to {}
            repeat with proc in (every process whose background only is false)
                try
                    set procName to name of proc
                    repeat with win in (every window of proc)
                        set windowEnd to procName & " - " & (name of win)
                        set end of windowList to windowEnd
                    end repeat
                end try
            end repeat
            return windowList
        end tell
        '''
        result = ExecutionService.run_applescript(script)
        stdout = result.get("stdout", "").strip()
        if stdout:
            return stdout
        return "Nenhuma janela encontrada."

    @staticmethod
    def move_window(app_name, x, y, width, height):
        """Move uma janela usando AppleScript."""
        script = f'''
        tell application "System Events"
            tell process "{app_name}"
                set position of front window to {{{x}, {y}}}
                set size of front window to {{{width}, {height}}}
            end tell
        end tell
        '''
        result = ExecutionService.run_applescript(script)
        if result.get("returncode") == 0:
            return f"Janela de {app_name} movida para ({x}, {y}) com tamanho ({width}, {height})."
        return f"Erro ao mover janela: {result.get('stderr', 'desconhecido')}"

    @staticmethod
    def focus_window(app_name):
        """Traz uma janela para frente."""
        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        result = ExecutionService.run_applescript(script)
        if result.get("returncode") == 0:
            return f"{app_name} em foco."
        return f"Erro ao focar {app_name}."
