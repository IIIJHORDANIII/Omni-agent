import sys
import os
import threading
import subprocess
import psutil
import time

# Configura o app para rodar apenas como agente de background (sem ícone no Dock)
if sys.platform == "darwin":
    from AppKit import NSBundle
    bundle = NSBundle.mainBundle()
    info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    if info:
        info["LSUIElement"] = "1"

# Ajusta o path para que os imports funcionem corretamente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path):
    """Retorna o caminho absoluto para recursos, funcionando em dev e bundle."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer
from core.registry import registry
from ui.chat_window import ChatWindow
from ui.hud import HUDOverlay
from utils.hotkeys import GlobalHotkeyHandler
from core.monitor_service import MonitorService
from core.hardware_manager import HardwareManager
from core.sound_service import SoundService
from core.briefing_service import BriefingService
from core.asset_manager import AssetManagerService
from core.log_watcher import LogWatcherService
from core.ghost_programmer import GhostPairProgrammer
from core.context_aggregator import ContextAggregator
from core.execution_service import ExecutionService
from core.terminal_server import TerminalOverwatchServer
from core.recall_service import RecallService
from core.night_watch import NightWatch
from core.auto_organizer import AutoOrganizerService
from ui.ghost_popup import GhostPopup

class MainApp(QApplication):
    _instance = None

    @staticmethod
    def instance():
        return MainApp._instance

    def __init__(self, argv):
        super().__init__(argv)
        MainApp._instance = self
        self.setQuitOnLastWindowClosed(False)

        # 0. Verificação de Setup (Versão PRO)
        if not os.path.exists(".env"):
            from ui.setup_wizard import SetupWizard
            wizard = SetupWizard()
            if wizard.exec() == SetupWizard.DialogCode.Rejected:
                sys.exit(0)
        
        # Hardware Setup...
        print("Sintonizando hardware de áudio...")
        HardwareManager.set_internal_mic_as_default()
        HardwareManager.set_input_volume(85)
        
        # Garante que o SwiftAgent esteja rodando
        self._ensure_swift_agent()
        
        # UI Components
        from ui.permission_gate import PermissionGate
        self.hud = HUDOverlay()
        self.chat_window = ChatWindow()
        self.ghost_popup = GhostPopup()
        self.ghost_popup.applied.connect(self._apply_ghost_fix)
        self.permission_gate = PermissionGate()
        
        # Registro de Serviços no Registry
        registry.register("hud", self.hud)
        registry.register("chat", self.chat_window)
        registry.register("voice", self.chat_window.voice_service)
        registry.register("llm", self.chat_window.llm_client)
        registry.register("permission_gate", self.permission_gate)
        
        # Referência compartilhada do VisionService (evita múltiplos carregamentos)
        shared_vision = self.chat_window.llm_client.vision_service
        
        # Recall Service (Memória Fotográfica)
        self.recall = RecallService(self.chat_window.llm_client.manager)
        self.recall.vision = shared_vision # Injeta a instância única
        
        # Night Watch (Patrulha Noturna)
        self.night_watch = NightWatch(self.chat_window.llm_client.manager)
        
        # Terminal Overwatch
        self.terminal_overwatch = TerminalOverwatchServer(callback=self._on_terminal_error)
        
        # Context Aggregator
        self.context_aggregator = ContextAggregator()
        self.context_timer = QTimer()
        self.context_timer.timeout.connect(self._update_context_wall)
        self.context_timer.start(10000) # Atualiza contexto a cada 10s
        
        # Sound Service
        self.sound = SoundService()
        
        # Central Watchdog Observer (Evita conflitos de FSEvents no macOS)
        from watchdog.observers import Observer
        self.file_observer = Observer()

        # Forge: Asset Manager (Otimização de imagens)
        self.asset_manager = AssetManagerService()
        # Auto-Organizer: Monitora e organiza downloads via IA
        self.organizer = AutoOrganizerService(self.chat_window.llm_client)
        # Background Agents: Linting, Dependency Scout, Commit Guard
        self.bg_agents = BackgroundAgentService(self)
        
        # Project DNA Crawler: Mapeia exaustivamente os projetos do Jhordan
        self.crawler = ProjectCrawlerService(self.chat_window.llm_client.manager)

        # Configura observadores (sem iniciar)
        self.asset_manager.start(observer=self.file_observer)
        self.organizer.start(observer=self.file_observer)
        self.bg_agents.start(observer=self.file_observer)
        
        # Auto-Organizer: Monitora e organiza downloads via IA
        self.organizer = AutoOrganizerService(self.chat_window.llm_client)
        self.organizer.start()
        
        # Overwatch: Log Watcher & Ghost Programmer
        self.log_watcher = LogWatcherService(
            self.chat_window.llm_client.manager,
            self.chat_window.voice_service,
            self.hud
        )
        
        self.ghost_programmer = GhostPairProgrammer(
            self.chat_window.llm_client.manager,
            self.chat_window.voice_service,
            self.hud
        )
        self.ghost_programmer.fix_suggested.connect(self.ghost_popup.show_suggestion)
        
        # Novas Proatividades 3.0
        from core.delta_vision import DeltaVisionService
        from core.time_guard import TimeGuardService
        self.delta_vision = DeltaVisionService(self.chat_window.voice_service, self.hud)
        self.time_guard = TimeGuardService(self.chat_window.voice_service, self.chat_window.llm_client)
        
        # Briefing Service
        self.briefing = BriefingService(self.chat_window.llm_client.manager)
        
        # Sentinela Service (Monitoramento Visual Adaptativo)
        self.sentinela = SentinelService(self.chat_window.voice_service, self.hud)
        
        # Services
        # O Monitor Service analisa a tela periodicamente em busca de eventos importantes
        self.monitor = MonitorService(
            self.chat_window.llm_client, 
            self.voice_service_alias if hasattr(self, 'voice_service_alias') else self.chat_window.voice_service,
            self.chat_window.llm_client.memory_client,
            hud=self.hud
        )
        self.monitor.vision = shared_vision # Injeta a instância única
        
        # Hotkey Handler (Lazy Init)
        self.hotkey_handler = GlobalHotkeyHandler()
        self.hotkey_handler.chat_requested.connect(self.chat_window.show_and_activate)
        self.hotkey_handler.voice_requested.connect(self.on_voice_requested)
        
        # Tray Icon Setup
        self.setup_tray()
        
        # Configura callback de status de voz para o HUD
        self.chat_window.voice_service.status_callback = lambda state, visible: self.hud.voice_signal.emit(state, visible)
        
        # Inicia o modo de escuta (Threads de áudio e coleta), mas sem o loop de Wake Word
        self.chat_window.voice_service.start_listening_mode()
        
        # Sequência de inicialização (Saudação personalizada)
        self.sound.play_system_sound("Hero")
        user_name = os.getenv("USER_NAME", "Senhor")
        self.chat_window.voice_service.speak(f"Sistemas online, {user_name}. Omniscient carregado.")
        
        # ESTABILIDADE PRO: Atraso na carga de serviços pesados para evitar conflito de hardware (SIGTRAP)
        print("Omniscient: Aguardando estabilização do hardware...")
        QTimer.singleShot(3000, self._start_delayed_services)
        
        # Briefing opcional no startup (Saudação baseada na hora - roda em background)
        threading.Thread(target=self._run_startup_briefing, daemon=True).start()
        
        print("Omniscient Agent iniciado e pronto!")

    def _start_delayed_services(self):
        """Inicia serviços que podem causar conflitos de hardware se iniciados em paralelo."""
        try:
            print("🚀 Iniciando Protocolos de Alta Fidelidade...")
            
            # 1. Hotkeys (O mais sensível no macOS)
            self.hotkey_handler.start()
            
            # 2. Visão e Monitoramento (Acionam o Metal)
            self.delta_vision.start()
            self.sentinela.start()
            self.monitor.start()
            
            # 3. Observadores de Arquivo e Logs
            self.file_observer.start()
            self.log_watcher.start()
            self.ghost_programmer.start()
            self.crawler.start_background_crawl()
            
            # 4. Serviços de Background
            self.night_watch.start()
            self.auto_organizer.start()
            self.background_agents.start()
            
            print("✅ Todos os sistemas operacionais e seguros.")
        except Exception as e:
            print(f"Erro ao iniciar serviços tardios: {e}")

    def _run_startup_briefing(self):
        """Gera um briefing proativo baseado em contexto real (Calendário, E-mail, Memória)."""
        print("Preparando briefing proativo...")
        time.sleep(4) # Aguarda sistemas estabilizarem
        
        try:
            # 1. Coleta contexto real
            cal_events = ExecutionService.get_calendar_events()
            unread_mails = ExecutionService.mail_unread(count=3)
            system_info = ExecutionService.get_system_info()
            
            prompt = f"""Gere um briefing de saudação curto e elegante para o JHORDAN.
            CONTEXTO REAL:
            - Calendário: {cal_events}
            - E-mails não lidos: {unread_mails}
            - Sistema: {system_info}
            
            REGRAS:
            - Seja muito breve (máximo 3 frases).
            - Não diga "bom dia" se for noite (veja a hora do sistema).
            - Mencione algo relevante do calendário ou e-mail se houver.
            - Termine com o status da bateria.
            """
            
            # Gera o briefing usando o cliente de chat para ter o tom do Omniscient
            briefing_text = self.chat_window.llm_client.chat([{"role": "user", "content": prompt}])
            
            if briefing_text and "Erro" not in briefing_text:
                self.hud.display_signal.emit("Briefing Matinal", "PROACTIVE", 5000)
                self.chat_window.voice_service.speak(briefing_text)
        except Exception as e:
            print(f"Erro ao gerar briefing proativo: {e}")

    def _update_context_wall(self):
        """Monitora o arquivo ativo e atualiza o HUD."""
        try:
            file_path = ExecutionService.get_vscode_current_file()
            if file_path and file_path != "unknown":
                data = self.context_aggregator.get_context_for_file(file_path)
                if data:
                    self.hud.context_signal.emit(data)
        except Exception as e:
            print(f"Erro ao atualizar context wall: {e}")

    def _on_terminal_error(self, payload):
        """Chamado quando um comando no terminal falha. Agora aprende com o erro."""
        command = payload.get("command", "")
        exit_code = payload.get("exit_code", "")
        output = payload.get("output", "")
        
        # 1. Verifica se já aprendemos sobre isso
        from core.error_learning import error_learner
        prior_knowledge = error_learner.check_for_prior_errors(command)
        
        prompt = f"""Você é o JARVIS. O usuário executou um comando que FALHOU no terminal.
COMANDO: {command}
CÓDIGO DE SAÍDA: {exit_code}
OUTPUT: {output}
{f'CONHECIMENTO PRÉVIO: {prior_knowledge}' if prior_knowledge else ''}

SUA TAREFA:
Explique rapidamente por que falhou e sugira o comando correto para consertar.
Seja extremamente breve (máximo 1 frase).
"""
        try:
            suggestion = self.chat_window.llm_client.manager.generate_command(prompt, system_context="TERMINAL_OVERWATCH")
            self.hud.display_signal.emit(f"FALHA NO TERMINAL: {suggestion}", "PROACTIVE", 7000)
            self.chat_window.voice_service.speak(f"Senhor, o comando {command.split()[0]} falhou. {suggestion}")
            
            # 2. Salva o novo conhecimento
            error_learner.learn_from_error(command, output or f"Exit code {exit_code}", suggestion)
            
        except Exception as e:
            print(f"Erro ao processar erro do terminal: {e}")

    def _apply_ghost_fix(self, file_path, old_text, new_text):
        """Aplica a correção sugerida pelo Ghost Programmer."""
        try:
            content = ExecutionService.read_file(file_path)
            if old_text in content:
                new_content = content.replace(old_text, new_text)
                ExecutionService.create_file(file_path, new_content)
                self.hud.display_signal.emit("CORREÇÃO APLICADA", "SUCCESS", 3000)
                self.sound.play_system_sound("Hero")
            else:
                self.hud.display_signal.emit("ERRO: Texto original não encontrado", "LISTENING", 3000)
        except Exception as e:
            print(f"Erro ao aplicar Ghost Fix: {e}")

    def _ensure_swift_agent(self):
        """Verifica se o binário Swift está rodando, se não, inicia."""
        swift_name = "Omniscient"
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == swift_name:
                return

        print("Swift Executor não encontrado. Iniciando...")
        # Procura o binário no bundle ou no local de desenvolvimento
        bundle_path = resource_path("Omniscient")
        dev_path_debug = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SwiftAgent/.build/arm64-apple-macosx/debug/Omniscient")
        dev_path_release = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SwiftAgent/.build/arm64-apple-macosx/release/Omniscient")

        # Prioridade: Bundle > Release > Debug
        path = None
        if os.path.exists(bundle_path): path = bundle_path
        elif os.path.exists(dev_path_release): path = dev_path_release
        elif os.path.exists(dev_path_debug): path = dev_path_debug

        if path:
            try:
                subprocess.Popen([path], start_new_session=True)
                time.sleep(2) # Aguarda o socket ser criado
            except Exception as e:
                print(f"Erro ao iniciar Swift Executor em {path}: {e}")
        else:
            print(f"Binário Swift não encontrado em {path}")

    def on_monitor_alert(self, message):

        """Chamado quando o Sentinela detecta algo importante na tela."""
        # Usa sinal para garantir thread-safety com a UI
        self.sound.notify()
        self.hud.display_signal.emit(f"SENTINELA: {message}", "PROACTIVE", 5000)
        self.chat_window.append_to_history(message, "system")

    def on_voice_requested(self):
        """Chamado via atalho Cmd+Shift+Enter. Alterna entre ouvir uma vez ou modo contínuo."""
        # Se o agente estiver falando, apenas interrompe o áudio
        if self.chat_window.voice_service.is_speaking:
            print("Atalho de voz acionado. Interrompendo fala...")
            self.chat_window.voice_service.stop_speaking()
            return

        # Alterna o estado do modo contínuo
        is_active = self.chat_window.voice_service.toggle_continuous_mode()
        
        if is_active:
            self.hud.display_signal.emit("MODO CONTÍNUO: ATIVADO", "LISTENING", 3000)
            self.sound.wake()
            self.sound.play_voice_start()
            
            # Só inicia a thread se ela já não estiver rodando
            if not getattr(self, "_voice_cycle_active", False):
                threading.Thread(target=self._acquire_and_process_command, daemon=True).start()
        else:
            self.hud.display_signal.emit("MODO CONTÍNUO: DESATIVADO", "IDLE", 3000)
            self.chat_window.voice_service.abort_listen = True
            self.sound.play_system_sound("Tink")

    def _acquire_and_process_command(self):
        """Loop principal de escuta. Mantém-se ativo enquanto o modo contínuo estiver ON."""
        self._voice_cycle_active = True
        try:
            while self.chat_window.voice_service.is_continuous_mode:
                # Se o agente começou a falar no meio do loop, espera ele terminar
                while self.chat_window.voice_service.is_speaking:
                    time.sleep(0.1)

                self.hud.voice_signal.emit("LISTENING", True)
                
                # Escuta o próximo comando (usando modo contínuo para evitar pre-buffer do wake word)
                text = self.chat_window.voice_service.listen(continuous_mode=True)
                
                if text and len(text.strip()) > 1:
                    # Processa o comando e gera a resposta (que dispara o speak)
                    self._handle_command_cycle(text)
                    # Dá um pequeno respiro para o processamento terminar e o speak começar
                    time.sleep(0.8)
                else:
                    # Se não houve áudio, apenas aguarda um pouco para não fritar a CPU
                    time.sleep(0.2)
                    
        finally:
            self._voice_cycle_active = False
            self.hud.voice_signal.emit("LISTENING", False)

    def _handle_command_cycle(self, text):
        """Processa um comando e abre a janela de conversa contínua."""
        self.hud.display_signal.emit("Processando...", "THINKING", 0)
        self.hud.voice_signal.emit("LISTENING", False)
        
        # Escuta o comando do usuário (usando o buffer contínuo)
        text = self.chat_window.voice_service.listen()
        
        if text and len(text.strip()) > 1:
            # Processa o comando inicial
            self._handle_command_cycle(text)
        else:
            self.hud.display_signal.emit("...", "IDLE", 1)
            self.hud.voice_signal.emit("LISTENING", False)
            print("Nenhum comando capturado após wake word.")

    def _handle_command_cycle(self, text):
        """Processa um comando e abre a janela de conversa contínua."""
        self.hud.display_signal.emit("Processando...", "THINKING", 0)
        self.hud.voice_signal.emit("LISTENING", False)
        
        print(f"Comando de voz: {text}")
        
        # Como process_silent_command é assíncrono (thread separada no chat_window),
        # precisamos aguardar ele terminar para reabrir o microfone.
        # Para simplificar e manter a fluidez, usamos uma abordagem de callback
        # ou chamamos a lógica de LLM diretamente, mas vamos aguardar o VoiceService terminar de falar.
        
        self.chat_window.process_silent_command(text)
        self.hud.display_signal.emit("Pronto.", "SUCCESS", 2000)
        
        # Loop de Conversa Contínua (Follow-up)
        # Aguarda o agente começar a falar (se for o caso)
        time.sleep(1) 
        
        # Aguarda ele terminar de falar
        while self.chat_window.voice_service.is_speaking:
            time.sleep(0.1)
            
        print("Abrindo janela de Conversa Contínua (Follow-up)...")
        self.hud.display_signal.emit("Ouvindo... (Contínuo)", "LISTENING", 0)
        self.hud.voice_signal.emit("LISTENING", True)
        
        # Escuta em modo contínuo (sem pre-buffer da wake word)
        follow_up_text = self.chat_window.voice_service.listen(continuous_mode=True)
        
        if follow_up_text and len(follow_up_text.strip()) > 1:
            # Se o usuário falou algo, entra no loop novamente
            self._handle_command_cycle(follow_up_text)
        else:
            # Se ficou em silêncio, encerra o ciclo e volta a dormir
            self.hud.display_signal.emit("Hibernando.", "IDLE", 2000)
            self.hud.voice_signal.emit("LISTENING", False)
            print("Fim do ciclo de voz. Aguardando wake word.")

    def setup_tray(self):
        # Tenta carregar o ícone, se não existir usa um padrão do sistema
        icon_path = resource_path("src/ui/icon.png")
        if sys.platform == "darwin":
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        else:
            self.tray_icon = QSystemTrayIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon), self)
            
        self.tray_icon.setToolTip("Omniscient Agent")
        self.chat_window.set_tray_icon(self.tray_icon)
        
        menu = QMenu()
        show_action = QAction("Abrir Chat", self)
        show_action.triggered.connect(self.chat_window.show_and_activate)
        
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self.quit)
        
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

if __name__ == "__main__":
    app = MainApp(sys.argv)
    sys.exit(app.exec())
