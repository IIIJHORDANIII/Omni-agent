import threading
from core.registry import registry
from PyQt6.QtCore import QEventLoop, QMetaObject, Qt, Q_ARG

class SafetyService:
    """
    Controlador de seguranca que intercepta acoes criticas.
    """
    CRITICAL_TOOLS = [
        "run_shell",
        "run_python",
        "vision_action",
        "github_create_pr",
        "mail_draft",
        "delete_file"
    ]

    # Timeout para aguardar aprovacao humana (em segundos)
    APPROVAL_TIMEOUT = 30

    @staticmethod
    def is_critical(tool_name, params=None):
        """Verifica se a ferramenta e critica, com excecoes para comandos de leitura."""
        if tool_name not in SafetyService.CRITICAL_TOOLS:
            return False

        # Excecao inteligente: Se for run_shell mas for apenas leitura (ls, grep, cat, find)
        if tool_name == "run_shell" and params:
            cmd = str(params.get("command", "")).lower()
            read_only_keywords = ["ls", "grep", "cat", "mdfind", "find", "list", "get", "whoami", "pwd"]
            if any(cmd.strip().startswith(kw) for kw in read_only_keywords) and not any(c in cmd for c in [">", "rm", "sudo"]):
                return False

        return True

    @staticmethod
    def request_human_approval(tool_name, params):
        """Bloqueia a execucao ate que o usuario aprove no HUD/Gate, com timeout."""
        gate = registry.get("permission_gate")
        if not gate:
            print("Safety: PermissionGate nao encontrado. Negando por seguranca.")
            return False

        # Cria um loop de eventos local para esperar a resposta
        loop = QEventLoop()
        result = [False]
        timed_out = [False]

        def on_confirmed(granted):
            result[0] = granted
            if not timed_out[0]:
                loop.quit()

        gate.confirmed.connect(on_confirmed)

        # Timer de timeout para evitar travamento infinito
        def _timeout_handler():
            timed_out[0] = True
            result[0] = False  # Timeout = negado
            try:
                loop.quit()
            except RuntimeError:
                pass

        timer = threading.Timer(SafetyService.APPROVAL_TIMEOUT, _timeout_handler)
        timer.daemon = True
        timer.start()

        # Formata a descricao para o usuario
        desc = f"<b>AUTORIZACAO NECESSARIA</b> (timeout: {SafetyService.APPROVAL_TIMEOUT}s)"
        desc += f"<br>Acao: {tool_name}"
        if params:
            cmd = params.get("command") or str(params)[:100]
            desc += f"<br><font color='#00d4ff'>$ {cmd}</font>"

        # Forca o gate a aparecer no topo
        QMetaObject.invokeMethod(gate, "request_permission", Qt.ConnectionType.QueuedConnection, Q_ARG(str, desc))

        loop.exec()
        timer.cancel()

        try:
            gate.confirmed.disconnect(on_confirmed)
        except (TypeError, RuntimeError):
            pass

        if timed_out[0]:
            print(f"Safety: Timeout apos {SafetyService.APPROVAL_TIMEOUT}s - acao negada.")

        return result[0]
