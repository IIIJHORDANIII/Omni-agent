import subprocess
import os
import pyperclip
from datetime import datetime
from core.execution_service import ExecutionService
from core.system_monitor import SystemMonitor

class ContextService:
    @staticmethod
    def get_active_window():
        """Obtém o nome do aplicativo e título da janela em foco via Swift."""
        try:
            response = ExecutionService.send_command_to_swift({"action": "get_active_app"})
            if response.get("status") == "ok":
                return f"{response.get('active_app', 'unknown')} - {response.get('window_title', 'Sem Título')}"
        except:
            pass
        return "Desconhecido"

    @staticmethod
    def get_clipboard():
        """Retorna os primeiros 100 caracteres do clipboard."""
        try:
            content = pyperclip.paste().strip()
            if content:
                return content[:100] + ("..." if len(content) > 100 else "")
        except:
            pass
        return "Vazio"

    @staticmethod
    def get_calendar_summary():
        """Lê eventos do calendário usando o ExecutionService."""
        try:
            events = ExecutionService.get_calendar_events()
            if isinstance(events, dict) and "stdout" in events:
                return events["stdout"].strip() or "Nenhum evento para hoje."
            return str(events)
        except:
            return "Indisponível"

    @staticmethod
    def get_recent_files():
        """Retorna arquivos modificados recentemente no diretório atual."""
        try:
            # Lista arquivos modificados nos últimos 60 min no diretório de trabalho
            cmd = "find . -mmin -60 -maxdepth 3 -not -path '*/.*' | head -n 8"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            files = result.stdout.strip()
            return files if files else "Nenhum arquivo modificado recentemente."
        except:
            return "Erro ao acessar arquivos."

    @staticmethod
    def get_selected_text():
        """Captura o texto selecionado na janela ativa via Swift."""
        try:
            response = ExecutionService.send_command_to_swift({"action": "get_selected_text"})
            if response.get("status") == "ok":
                return response.get("selected_text", "")
        except:
            pass
        return ""

    @staticmethod
    def get_full_context():
        """Consolida todo o contexto do sistema para injetar na LLM."""
        resources = SystemMonitor.get_resource_usage()
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "active_window": ContextService.get_active_window(),
            "selected_text": ContextService.get_selected_text(),
            "clipboard": ContextService.get_clipboard(),
            "recent_files": ContextService.get_recent_files(),
            "cwd": os.getcwd(),
            "system": resources
        }

    @staticmethod
    def get_context_str():
        """Retorna o contexto formatado como string para o prompt."""
        ctx = ContextService.get_full_context()
        sys = ctx['system']
        sel_text = ctx['selected_text']
        sel_str = f"Texto Selecionado: {sel_text[:200]}..." if sel_text else "Nenhum texto selecionado."
        
        return (
            f"--- CONTEXTO DO SISTEMA ---\n"
            f"Data/Hora: {ctx['timestamp']}\n"
            f"Janela em Foco: {ctx['active_window']}\n"
            f"{sel_str}\n"
            f"Clipboard: {ctx['clipboard']}\n"
            f"Status do Mac: CPU {sys['cpu']}% | Memória {sys['memory']}% | Bateria {sys['battery']['percent']}% "
            f"({'Ligado na força' if sys['battery']['power_plugged'] else 'Na bateria'})\n"
            f"---------------------------"
        )
