from core.execution_service import ExecutionService

class LayoutManager:
    @staticmethod
    def organize_work_layout():
        """Organiza o layout de trabalho: Safari na esquerda, VS Code na direita."""
        import time
        # 1. Safari
        ExecutionService.send_command_to_swift({
            "action": "move_window", 
            "app": "com.apple.Safari", 
            "x": 0.0, "y": 0.0, 
            "w": 960.0, "h": 1080.0
        })
        # 2. VS Code (assumindo bundle id)
        ExecutionService.send_command_to_swift({
            "action": "move_window", 
            "app": "com.microsoft.VSCode", 
            "x": 960.0, "y": 0.0, 
            "w": 960.0, "h": 1080.0
        })
        
        # Pequena pausa para o Window Manager processar
        time.sleep(0.5)
        
        # 3. Trazer foco
        ExecutionService.send_command_to_swift({"action": "bring_to_front", "app": "com.apple.Safari"})
        
        return "Layout de trabalho organizado."

    @staticmethod
    def close_all_apps(app_list):
        """Fecha uma lista de apps."""
        for app in app_list:
            ExecutionService.send_command_to_swift({"action": "close_app", "app": app})
        return "Apps fechados."
