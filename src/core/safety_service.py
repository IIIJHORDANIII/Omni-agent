from core.registry import registry
from PyQt6.QtCore import QEventLoop, QMetaObject, Qt, Q_ARG

class SafetyService:
    """
    Controlador de segurança que intercepta ações críticas.
    """
    CRITICAL_TOOLS = [
        "run_shell", 
        "run_python", 
        "vision_action", 
        "github_create_pr", 
        "mail_draft", # Embora seja rascunho, pode ser sensível
        "delete_file"
    ]

    @staticmethod
    def is_critical(tool_name):
        return tool_name in SafetyService.CRITICAL_TOOLS

    @staticmethod
    def request_human_approval(tool_name, params):
        """Bloqueia a execução até que o usuário aprove no HUD/Gate."""
        gate = registry.get("permission_gate")
        if not gate: 
            print("Safety: PermissionGate não encontrado. Negando por segurança.")
            return False

        # Cria um loop de eventos local para esperar a resposta sem travar o Agente
        loop = QEventLoop()
        result = [False]

        def on_confirmed(granted):
            result[0] = granted
            loop.quit()

        gate.confirmed.connect(on_confirmed)
        
        # Formata a descrição
        desc = f"Executar ferramenta: <b>{tool_name}</b>"
        if params:
            desc += f"<br><small>{str(params)[:100]}...</small>"
            
        # Chama o UI update na main thread
        QMetaObject.invokeMethod(gate, "request_permission", Qt.ConnectionType.QueuedConnection, Q_ARG(str, desc))
        
        loop.exec() # Espera o sinal 'confirmed'
        
        gate.confirmed.disconnect(on_confirmed)
        return result[0]
