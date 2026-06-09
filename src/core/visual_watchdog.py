import time
from core.visual_service import find_element
from core.execution_service import ExecutionService

class VisualWatchdog:
    # Mapeamento de templates para ações
    # Exemplo: {"path/to/error_button.png": "close_app_action"}
    MONITORED_ELEMENTS = {
        "ui_elements/error_popup.png": "close_error",
    }
    
    @staticmethod
    def scan():
        """Escaneia a tela em busca de elementos de interface críticos."""
        for template_path, action in VisualWatchdog.MONITORED_ELEMENTS.items():
            coords = find_element(template_path)
            if coords:
                print(f"Watchdog: Elemento {template_path} detectado em {coords}. Ação: {action}")
                # Dispatcher de ação via Socket Swift
                ExecutionService.send_command_to_swift({"action": "click_at", "x": coords[0], "y": coords[1]})
                return True
        return False
