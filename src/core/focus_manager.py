import time
from core.system_monitor import SystemMonitor
from core.hardware_manager import HardwareManager

class FocusManager:
    # Mapeamento de apps para comportamentos
    APP_RULES = {
        "com.microsoft.VSCode": {"volume": 0, "brightness": 100},
        "com.apple.Safari": {"volume": 30, "brightness": 80},
        "us.zoom.xos": {"volume": 80, "dnd": True, "action": "open_app", "params": {"app": "Notes"}},
        "com.google.Chrome": {"volume": 40}, # Chrome é genérico, mas bom ter
        "com.apple.mail": {"volume": 20},
    }
    
    _last_active_app = None

    @staticmethod
    def monitor_and_adapt():
        """Monitora o app em foco e adapta o hardware."""
        active_app_resp = SystemMonitor.get_active_app()
        active_app = active_app_resp.get("active_app")
        
        if active_app != FocusManager._last_active_app:
            print(f"DEBUG: App mudou para {active_app}")
            FocusManager._last_active_app = active_app
            
            if active_app in FocusManager.APP_RULES:
                rules = FocusManager.APP_RULES[active_app]
                print(f"DEBUG: Aplicando regras para {active_app}: {rules}")
                
                if "volume" in rules:
                    HardwareManager.set_volume(rules["volume"])
                if "brightness" in rules:
                    HardwareManager.set_brightness(rules["brightness"])
                if rules.get("dnd"):
                    HardwareManager.manage_hardware("do_not_disturb")
                
                # Executa ação extra se houver
                if "action" in rules:
                    from core.tool_dispatcher import ToolDispatcher
                    ToolDispatcher.dispatch({
                        "tool": rules["action"],
                        "params": rules.get("params", {})
                    })
            else:
                print(f"DEBUG: Sem regras específicas para {active_app}")

    @staticmethod
    def start_monitoring(interval=2.0):
        """Loop infinito de monitoramento."""
        print("Iniciando monitoramento de foco...")
        try:
            while True:
                FocusManager.monitor_and_adapt()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Monitoramento parado.")
