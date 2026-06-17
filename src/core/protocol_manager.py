import time
from core.execution_service import ExecutionService


class ProtocolManager:
    """
    Gerencia sequencias complexas de comandos proativos (Protocolos).
    """

    @staticmethod
    def run_protocol(name, llm_manager=None):
        """Executa um protocolo pelo nome."""
        print(f"ATIVANDO PROTOCOLO: {name}")

        if name == "AUTOCURA":
            return ProtocolManager._protocol_autocura(llm_manager)
        elif name == "SMART_COMMIT":
            return ProtocolManager._protocol_smart_commit(llm_manager)
        elif name == "RETROSPECTIVA":
            return ProtocolManager._protocol_retrospectiva(llm_manager)
        elif name == "VIGIA":
            return ProtocolManager._protocol_vigia(llm_manager)
        elif name == "NIGHT_WATCH":
            return ProtocolManager._protocol_night_watch(llm_manager)
        elif name == "DEEP_WORK":
            return ProtocolManager._protocol_deep_work()
        elif name == "CLONE_UI":
            return ProtocolManager._protocol_clone_ui(llm_manager)
        elif name == "LIMPEZA_DESKTOP":
            return ProtocolManager._protocol_cleanup()
        elif name == "ECONOMIA_ENERGIA":
            return ProtocolManager._protocol_power_save()
        else:
            return f"Protocolo {name} nao reconhecido."

    @staticmethod
    def _protocol_autocura(llm):
        """Protocolo para detectar erro no terminal e sugerir correcao."""
        import subprocess
        print("Analisando falhas recentes no sistema...")

        errors = []
        try:
            result = subprocess.run(
                ['log', 'show', '--predicate', 'eventMessage contains "error" or eventMessage contains "Error"',
                 '--last', '30m', '--style', 'compact'],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                errors = lines[-10:]
        except Exception:
            pass

        try:
            result = subprocess.run(
                ['log', 'show', '--predicate', 'eventMessage contains "crash" or eventMessage contains "abort"',
                 '--last', '1h', '--style', 'compact'],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                errors.extend(result.stdout.strip().split('\n')[-5:])
        except Exception:
            pass

        if not errors:
            return "Protocolo de Autocura: Nenhuma falha recente detectada. Sistema saudavel."

        error_text = "\n".join(errors[:20])
        prompt = f"""Analise estes erros recentes do sistema e sugira correcoes:

ERROS:
{error_text}

Forneca:
1. Resumo dos problemas encontrados
2. Possiveis causas
3. Acoes corretivas sugeridas"""

        analysis = llm.generate_command(prompt, system_context="AUTOCURA_ANALYSIS")
        return f"Protocolo de Autocura concluido.\n\n{analysis}"

    @staticmethod
    def _protocol_cleanup():
        """Organiza a mesa (Desktop) movendo arquivos para pastas logicas."""
        import os
        import shutil

        desktop_path = os.path.expanduser("~/Desktop")
        if not os.path.exists(desktop_path):
            return "Desktop nao encontrado."

        categories = {
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg"],
            "Videos": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".swift"],
            "Archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".dmg"],
            "Spreadsheets": [".csv", ".xlsx", ".xls", ".numbers"],
        }

        moved = 0
        skipped = 0

        for item in os.listdir(desktop_path):
            item_path = os.path.join(desktop_path, item)
            if os.path.isdir(item_path) or item.startswith('.'):
                skipped += 1
                continue

            ext = os.path.splitext(item)[1].lower()
            target_folder = None
            for folder, extensions in categories.items():
                if ext in extensions:
                    target_folder = folder
                    break

            if target_folder:
                dest_dir = os.path.join(desktop_path, target_folder)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, item)
                if not os.path.exists(dest):
                    shutil.move(item_path, dest)
                    moved += 1
                else:
                    skipped += 1
            else:
                skipped += 1

        return f"Protocolo de Limpeza: {moved} arquivos movidos, {skipped} ignorados."

    @staticmethod
    def _protocol_power_save():
        """Reduz brilho e volume, ativa modo de baixo consumo."""
        from core.hardware_manager import HardwareManager

        ExecutionService.set_system_volume(15)
        HardwareManager.set_brightness(10)
        ExecutionService.toggle_dark_mode(True)

        heavy_apps = ["com.spotify.client", "com.tinyspeck.slackmacgap", "com.discordapp.Discord"]
        closed = 0
        for app in heavy_apps:
            try:
                import subprocess
                result = subprocess.run(['pgrep', '-f', app], capture_output=True, text=True)
                if result.stdout.strip():
                    subprocess.run(['killall', app.split('.')[-1]], capture_output=True)
                    closed += 1
            except Exception:
                pass

        return f"Protocolo de Economia de Energia Ativado. Volume: 15%, Brilho: 10%, Dark Mode: ON, {closed} apps pesados fechados."

    @staticmethod
    def _protocol_deep_work():
        """Ativa o modo de foco supremo (Dark Mode, DND, Musica, Fecha Distractions)."""
        print("Ativando Protocolo DEEP WORK...")

        ExecutionService.toggle_dark_mode(True)
        ExecutionService.set_dnd(True)

        ExecutionService.set_system_volume(30)
        from core.hardware_manager import HardwareManager
        HardwareManager.set_brightness(40)

        distractors = ["com.apple.iChat", "com.tinyspeck.slack", "com.hnc.Discord", "WhatsApp"]
        for app in distractors:
            ExecutionService.send_command_to_swift({"action": "close_app", "app": app})

        ExecutionService.open_app("Visual Studio Code")
        ExecutionService.manage_music("Music", "play")

        return "Protocolo DEEP WORK Ativado. Foco total, Senhor."

    @staticmethod
    def _protocol_clone_ui(llm):
        """Captura a tela e gera codigo HTML/Tailwind para clonar a UI visivel."""
        print("Iniciando Protocolo de Clonagem de UI...")
        from core.vision_service import VisionService
        vision = VisionService()

        description = vision.describe_screen("Descreva detalhadamente o elemento de UI central nesta tela: cores, espacamento, sombras, fontes e estrutura HTML/Tailwind.")

        if "Erro" in description:
            return "Falha na analise visual."

        prompt = f"""Voce e um mestre em Front-end (React/Tailwind).
Com base na descricao visual abaixo, gere o codigo exato para replicar este elemento.

DESCRICAO VISUAL:
{description}

REGRAS:
1. Use React + Tailwind CSS.
2. Forneca APENAS o codigo do componente, sem explicacoes.
3. Garanta que as cores e sombras sejam fieis a descricao.
"""
        code = llm.generate_command(prompt, system_context="UI_CLONING_FORGE").strip()

        ExecutionService.manage_clipboard("write", code)
        return "UI Clonada com Sucesso! O codigo React/Tailwind esta no seu Clipboard."

    @staticmethod
    def _protocol_retrospectiva(llm):
        """Protocolo de encerramento de dia: Cruza Linear, GitHub e Memoria."""
        from core.linear_service import LinearService
        from core.github_service import GithubService
        from core.briefing_service import BriefingService
        from core.memory_client import MemoryClient

        linear = LinearService()
        github = GithubService()
        briefing = BriefingService(llm)
        memory = MemoryClient()

        print("Coletando progresso do Linear...")
        l_info = linear.get_completed_issues_today()
        print("Coletando progresso do GitHub...")
        g_info = github.get_recent_activity()

        print("Gerando retrospectiva via LLM...")
        retro_text = briefing.generate_evening_briefing(l_info, g_info)

        try:
            memory.store_observation(f"Retrospectiva do dia: {retro_text}")
        except Exception:
            pass

        return retro_text

    @staticmethod
    def _protocol_vigia(llm):
        """Ativa a vigilancia visual para documentacao de arquitetura."""
        from core.vigia_service import VigiaService
        vigia = VigiaService(llm)
        vigia.start_vigilance()
        path = vigia.check_and_document()
        if path:
            return f"Protocolo VIGIA ativado. Documentacao inicial gerada em: {path}"
        return "Protocolo VIGIA ativado. Aguardando deteccao de apps de design."

    @staticmethod
    def _protocol_night_watch(llm):
        """Dispara a patrulha noturna manualmente."""
        from core.night_watch import NightWatch
        nw = NightWatch(llm)
        nw.run_nightly_patrol()
        return "Patrulha Night Watch concluida. Verifique os branches 'jarvis/night-watch-*' se houveram correcoes."
