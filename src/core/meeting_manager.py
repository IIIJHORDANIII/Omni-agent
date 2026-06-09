import time
import re
from datetime import datetime, timedelta
from core.layout_manager import LayoutManager
from core.hardware_manager import HardwareManager
from core.execution_service import ExecutionService

class MeetingManager:
    @staticmethod
    def run_meeting_routine():
        """Rotina para preparar o Mac para reuniões."""
        print("Preparando para reunião...")
        
        # 1. Hardware
        HardwareManager.toggle_mute() # Garante silêncio inicial
        HardwareManager.set_brightness(70)
        
        # 2. Fechar distrações
        LayoutManager.close_all_apps(["com.hnc.Discord", "com.apple.mail"])
        
        # 3. Trazer app de reunião para frente (Exemplo: Safari ou Zoom)
        # Você pode melhorar essa lógica para identificar qual app abrir
        ExecutionService.send_command_to_swift({"action": "bring_to_front", "app": "com.apple.Safari"})
        
        return "Modo Reunião Ativado."

    @staticmethod
    def check_and_start_meeting():
        """Verifica se há reunião em breve e ativa o modo."""
        result = ExecutionService.get_calendar_events()
        # Corrige: extrai a string 'stdout' do dicionário retornado pelo AppleScript
        events = result.get("stdout", "")
        
        if not events or events.strip() == "":
            return "Sem reuniões próximas."
            
        # Parsing simples da string retornada pelo AppleScript
        # Formato esperado: "Título às data"
        lines = events.strip().split('\n')
        
        for line in lines:
            # Exemplo de regex para extrair data (ajuste conforme o formato do seu Mac)
            match = re.search(r' às (.+)', line)
            if match:
                # Nota: Parsing de data em AppleScript é complexo. 
                # Se o evento for "hoje", assumimos que é uma reunião próxima.
                if "hoje" in line.lower() or "today" in line.lower():
                    print(f"Reunião encontrada: {line}")
                    return MeetingManager.run_meeting_routine()
                    
        return "Nenhuma reunião iminente."
