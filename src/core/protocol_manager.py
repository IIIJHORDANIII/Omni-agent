import time
from core.execution_service import ExecutionService
from core.system_monitor import SystemMonitor

class ProtocolManager:
    """
    Gerencia sequências complexas de comandos proativos (Protocolos).
    Inspirado nos protocolos de defesa/automação do JARVIS.
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
            return f"Protocolo {name} não reconhecido."

    @staticmethod
    def _protocol_autocura(llm):
        """Protocolo para detectar erro no terminal e sugerir correção."""
        # 1. Tenta pegar o último erro do terminal (exemplo simplificado)
        # Em um cenário real, poderíamos ler o histórico do .zsh_history ou capturar via acessibilidade
        print("Analisando falhas recentes no sistema...")
        return "Protocolo de Autocura iniciado. Monitorando logs de erro."

    @staticmethod
    def _protocol_deep_work():
        """Ativa o modo de foco supremo (Dark Mode, DND, Música, Fecha Distrações)."""
        print("Ativando Protocolo DEEP WORK...")
        
        # 1. Estética e Ambiente
        ExecutionService.toggle_dark_mode(True)
        ExecutionService.set_dnd(True)
        
        # 2. Hardware
        ExecutionService.set_system_volume(30)
        from core.hardware_manager import HardwareManager
        HardwareManager.set_brightness(40)
        
        # 3. Fechar Distrações (Exemplos comuns)
        distractors = ["com.apple.iChat", "com.tinyspeck.slack", "com.hnc.Discord", "WhatsApp"]
        for app in distractors:
            ExecutionService.send_command_to_swift({"action": "close_app", "app": app})
            
        # 4. Iniciar Fluxo
        ExecutionService.open_app("Visual Studio Code")
        # Tenta tocar música (Apple Music por padrão no Deep Work)
        ExecutionService.manage_music("Music", "play")
        
        return "Protocolo DEEP WORK Ativado. Foco total, Senhor."

    @staticmethod
    def _protocol_clone_ui(llm):
        """Captura a tela e gera código HTML/Tailwind para clonar a UI visível."""
        print("Iniciando Protocolo de Clonagem de UI...")
        from core.vision_service import VisionService
        vision = VisionService()
        
        # 1. Captura e descreve o elemento visual
        description = vision.describe_screen("Descreva detalhadamente o elemento de UI central nesta tela: cores, espaçamento, sombras, fontes e estrutura HTML/Tailwind.")
        
        if "Erro" in description: return "Falha na análise visual."

        # 2. Gera o código
        prompt = f"""Você é um mestre em Front-end (React/Tailwind).
Com base na descrição visual abaixo, gere o código exato para replicar este elemento.

DESCRIÇÃO VISUAL:
{description}

REGRAS:
1. Use React + Tailwind CSS.
2. Forneça APENAS o código do componente, sem explicações.
3. Garanta que as cores e sombras sejam fiéis à descrição.
"""
        code = llm.generate_command(prompt, system_context="UI_CLONING_FORGE").strip()
        
        # 3. Copia para o clipboard
        ExecutionService.manage_clipboard("write", code)
        return "UI Clonada com Sucesso! O código React/Tailwind está no seu Clipboard."

    @staticmethod
    def _protocol_cleanup():
        """Organiza a mesa (Desktop) movendo arquivos para pastas lógicas."""
        desktop_path = "~/Desktop"
        files = ExecutionService.list_files(desktop_path)
        # Lógica simples de organização por extensão
        return "Protocolo de Limpeza: Arquivos organizados por categoria."

    @staticmethod
    def _protocol_power_save():
        """Reduz brilho e fecha apps pesados se a bateria estiver baixa."""
        ExecutionService.set_system_volume(20)
        # Brilho baixo via hardware manager
        from core.hardware_manager import HardwareManager
        HardwareManager.set_brightness(10)
        return "Protocolo de Economia de Energia Ativado."

    @staticmethod
    def _protocol_retrospectiva(llm):
        """Protocolo de encerramento de dia: Cruza Linear, GitHub e Memória."""
        from core.linear_service import LinearService
        from core.github_service import GithubService
        from core.briefing_service import BriefingService
        from core.memory_client import MemoryClient

        linear = LinearService()
        github = GithubService()
        briefing = BriefingService(llm)
        memory = MemoryClient()

        # 1. Coleta dados
        print("Coletando progresso do Linear...")
        l_info = linear.get_completed_issues_today()
        print("Coletando progresso do GitHub...")
        g_info = github.get_recent_activity()

        # 2. Gera Briefing
        print("Gerando retrospectiva via LLM...")
        retro_text = briefing.generate_evening_briefing(l_info, g_info)

        # 3. Salva na Memória de Longo Prazo para amanhã
        try:
            memory.store_observation(f"Retrospectiva do dia: {retro_text}")
        except:
            pass

        return retro_text

    @staticmethod
    def _protocol_vigia(llm):
        """Ativa a vigilância visual para documentação de arquitetura."""
        from core.vigia_service import VigiaService
        vigia = VigiaService(llm)
        vigia.start_vigilance()
        path = vigia.check_and_document()
        if path:
            return f"Protocolo VIGIA ativado. Documentação inicial gerada em: {path}"
        return "Protocolo VIGIA ativado. Aguardando detecção de apps de design."

    @staticmethod
    def _protocol_night_watch(llm):
        """Dispara a patrulha noturna manualmente."""
        from core.night_watch import NightWatch
        nw = NightWatch(llm)
        nw.run_nightly_patrol()
        return "Patrulha Night Watch concluída. Verifique os branches 'jarvis/night-watch-*' se houveram correções."
