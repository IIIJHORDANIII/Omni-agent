import time
from core.layout_manager import LayoutManager
from core.hardware_manager import HardwareManager
from core.system_monitor import SystemMonitor
from core.execution_service import ExecutionService
from core.visual_service import find_element

class AutomationOrchestrator:
    
    # 1. Active Monitoring (Smart Focus Mode)
    @staticmethod
    def run_smart_focus(interval=1.0):
        """Monitora foco e aplica regras de hardware."""
        print("Iniciando modo de foco inteligente...")
        last_app = None
        while True:
            active_app = SystemMonitor.get_active_app().get("active_app")
            if active_app != last_app:
                print(f"App em foco: {active_app}")
                # Exemplo: Se Safari, brilho 80%, se Terminal, volume 0%
                if active_app == "com.apple.Safari":
                    HardwareManager.set_brightness(80)
                elif active_app == "com.apple.Terminal":
                    HardwareManager.set_volume(0)
                last_app = active_app
            time.sleep(interval)

    # 2. Visual Control
    @staticmethod
    def visual_action(template_path):
        """Executa um clique baseado em visão computacional usando o executor Swift."""
        coords = find_element(template_path)
        if coords:
            x, y = coords
            ExecutionService.send_command_to_swift({"action": "click_at", "x": float(x), "y": float(y)})
            return f"Sucesso: Clicado em ({x}, {y})"
        return "Falha: Elemento não encontrado."

    # 3. Rituals
    @staticmethod
    def run_deep_work_ritual():
        """Prepara o ambiente para foco total."""
        print("Executando ritual de Deep Work...")
        # 1. Silenciar sistema
        ExecutionService.set_system_volume(0)
        # 2. Ativar Não Perturbe (DND)
        ExecutionService.manage_hardware("do_not_disturb")
        # 3. Fechar apps distrativos (ex: Slack, WhatsApp)
        # ExecutionService.send_command_to_swift({"action": "close_app", "app": "WhatsApp"})
        # 4. Abrir app de foco (ex: Obsidian ou VS Code)
        ExecutionService.open_app("Visual Studio Code")
        return "Modo Deep Work Ativado. Boa sorte."

    # 4. Event Orchestration
    @staticmethod
    def sync_calendar_to_reminders():
        """Lê o calendário e cria lembretes para eventos de hoje."""
        events = ExecutionService.get_calendar_events()
        if events:
            ExecutionService.add_reminder(f"Eventos de hoje: {events[:50]}...")
            return "Eventos sincronizados."
        return "Nenhum evento encontrado."
