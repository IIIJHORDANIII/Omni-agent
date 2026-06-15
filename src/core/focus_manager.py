import time
import threading
from core.system_monitor import SystemMonitor
from core.hardware_manager import HardwareManager

class FocusManager:
    # Mapeamento de apps para comportamentos
    APP_RULES = {
        "com.microsoft.VSCode": {"volume": 0, "brightness": 100},
        "com.apple.Safari": {"volume": 30, "brightness": 80},
        "us.zoom.xos": {"volume": 80, "dnd": True, "action": "open_app", "params": {"app": "Notes"}},
        "com.google.Chrome": {"volume": 40},
        "com.apple.mail": {"volume": 20},
    }
    
    _last_active_app = None
    _monitoring = False

    @staticmethod
    def monitor_and_adapt():
        """Monitora o app em foco e adapta o hardware."""
        try:
            active_app_resp = SystemMonitor.get_active_app()
            if not isinstance(active_app_resp, dict):
                return
            active_app = active_app_resp.get("active_app")
            
            if active_app != FocusManager._last_active_app:
                FocusManager._last_active_app = active_app
                
                if active_app in FocusManager.APP_RULES:
                    rules = FocusManager.APP_RULES[active_app]
                    
                    if "volume" in rules:
                        HardwareManager.set_volume(rules["volume"])
                    if "brightness" in rules:
                        HardwareManager.set_brightness(rules["brightness"])
                    if rules.get("dnd"):
                        HardwareManager.send_command_to_swift({"action": "toggle_dnd"})
                    
                    # Executa ação extra se houver
                    if "action" in rules:
                        from core.tool_dispatcher import ToolDispatcher
                        ToolDispatcher.dispatch({
                            "tool": rules["action"],
                            "params": rules.get("params", {})
                        })
        except Exception as e:
            print(f"FocusManager: Erro ao monitorar foco: {e}")

    @staticmethod
    def start_monitoring(interval=2.0):
        """Inicia monitoramento de foco em background thread."""
        if FocusManager._monitoring:
            return
        FocusManager._monitoring = True
        
        def _monitor_loop():
            print("FocusManager: Monitoramento de foco ativo.")
            while FocusManager._monitoring:
                FocusManager.monitor_and_adapt()
                time.sleep(interval)
        
        thread = threading.Thread(target=_monitor_loop, daemon=True)
        thread.start()
