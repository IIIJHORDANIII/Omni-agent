import sys
import os
import multiprocessing
import threading
import subprocess
import psutil
import time
from dotenv import load_dotenv  # keep for .env loading

# CRÍTICO: Previne loop infinito de instâncias no modo empacotado (.app)
# Deve ser a primeira coisa no arquivo, antes de qualquer import pesado
if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    # Proteção adicional (Kill Switch) contra bibliotecas que tentam
    # dar spawn passando "-c" (comum no macOS) e escapando do freeze_support.
    if getattr(sys, 'frozen', False) and len(sys.argv) > 1 and sys.argv[1] == '-c':
        sys.exit(0)

# Desativa telemetria do ChromaDB ANTES de importar o módulo
# Evita crash do posthog e loops de multiprocessing gerados por telemetria
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Caminho persistente para o arquivo .env
ENV_PATH = os.path.expanduser("~/.config/anders/.env")

def resource_path(relative_path):
    """Retorna o caminho absoluto para recursos, funcionando em dev e bundle."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Ajusta o path para que os imports funcionem corretamente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QLockFile

from core.registry import registry
from ui.chat_window import ChatWindow
from ui.spotlight_chat import SpotlightChat
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
from core.background_agents import BackgroundAgentService
from core.crawler_service import ProjectCrawlerService
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
        
        # Configura o app para rodar apenas como agente de background no macOS
        if sys.platform == "darwin":
            try:
                from AppKit import NSBundle
                bundle = NSBundle.mainBundle()
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info:
                    info["LSUIElement"] = "1"
            except Exception as e:
                print(f"Aviso: Não foi possível definir LSUIElement: {e}")

        # Setup wizard removed: configuration is expected to exist at ENV_PATH.
        if not os.path.exists(ENV_PATH):
            os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
            open(ENV_PATH, 'a').close()
        if not os.path.exists(ENV_PATH):
            os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
            from ui.setup_wizard import SetupWizard
            wizard = SetupWizard()
            if wizard.exec() == SetupWizard.DialogCode.Rejected:
                sys.exit(0)
        
        load_dotenv(ENV_PATH, override=True)
        # Carrega variáveis de configuração adicionais
        from core.config_loader import load_user_config
        load_user_config()
        # O gerenciamento de LLMs locais foi removido; use APIs externas conforme configurado.

        from core.llm_manager import LLMManager
        _detected_provider = LLMManager._detect_provider()
        print(f"Anders: Provider detectado = {_detected_provider}")
        
        # Hardware Setup
        print("Sintonizando hardware de áudio...")
        HardwareManager.set_internal_mic_as_default()
        HardwareManager.set_input_volume(85)
        
        # Garante que o SwiftAgent esteja rodando
        self._ensure_swift_agent()
        
        # UI Components
        from ui.permission_gate import PermissionGate
        self.hud = HUDOverlay()
        self.chat_window = ChatWindow()
        self.spotlight = SpotlightChat()
        self.ghost_popup = GhostPopup()
        self.ghost_popup.applied.connect(self._apply_ghost_fix)
        self.permission_gate = PermissionGate()
        
        # Registro de Serviços
        registry.register("hud", self.hud)
        registry.register("chat", self.chat_window)
        registry.register("voice", self.chat_window.voice_service)
        registry.register("llm", self.chat_window.llm_client)
        registry.register("permission_gate", self.permission_gate)
        
        # Conexões
        voice_svc = self.chat_window.voice_service
        voice_overlay = self.hud.voice_overlay
        voice_svc.amplitude_callback = lambda amp: voice_overlay.set_spectrum([amp] * 20) # Fallback simples
        voice_svc.spectrum_callback = lambda spec: voice_overlay.set_spectrum(spec)
        
        # Conecta o speaker (Kokoro) ao HUD também
        if hasattr(self.chat_window.voice_service, 'kokoro'):
            self.chat_window.voice_service.kokoro.spectrum_callback = lambda spec: voice_overlay.set_spectrum(spec)
        
        self.shared_vision = self.chat_window.llm_client.vision_service
        self.recall = RecallService(self.chat_window.llm_client.manager)
        self.recall.vision = self.shared_vision
        
        self.night_watch = NightWatch(self.chat_window.llm_client.manager)
        self.terminal_overwatch = TerminalOverwatchServer(callback=self._on_terminal_error)
        
        self.context_aggregator = ContextAggregator()
        self.context_timer = QTimer()
        self.context_timer.timeout.connect(self._update_context_wall)
        self.context_timer.start(10000)
        
        self.sound = SoundService()
        
        from watchdog.observers import Observer
        self.file_observer = Observer()

        self.asset_manager = AssetManagerService()
        self.organizer = AutoOrganizerService(self.chat_window.llm_client)
        self.bg_agents = BackgroundAgentService(self)
        self.crawler = ProjectCrawlerService(self.chat_window.llm_client.manager)

        self.asset_manager.start(observer=self.file_observer)
        self.organizer.start(observer=self.file_observer)
        self.bg_agents.start(observer=self.file_observer)
        
        self.log_watcher = LogWatcherService(self.chat_window.llm_client.manager, self.chat_window.voice_service, self.hud)
        self.ghost_programmer = GhostPairProgrammer(self.chat_window.llm_client.manager, self.chat_window.voice_service, self.hud)
        self.ghost_programmer.fix_suggested.connect(self.ghost_popup.show_suggestion)
        
        from core.delta_vision import DeltaVisionService
        from core.time_guard import TimeGuardService
        self.delta_vision = DeltaVisionService(self.chat_window.voice_service, self.hud)
        self.time_guard = TimeGuardService(self.chat_window.voice_service, self.chat_window.llm_client)
        
        self.briefing = BriefingService(self.chat_window.llm_client.manager)
        
        self.monitor = MonitorService(
            self.chat_window.llm_client, 
            self.chat_window.voice_service,
            self.chat_window.llm_client.memory_client,
            hud=self.hud
        )
        self.monitor.vision = self.shared_vision
        
        self.hotkey_handler = GlobalHotkeyHandler()
        # Connect Spotlight shortcut
        self.hotkey_handler.spotlight_requested.connect(self.spotlight.show_overlay)
        # Chat shortcut disabled (no connection)
        # self.hotkey_handler.chat_requested.connect(self.chat_window.show_and_activate)
        self.hotkey_handler.voice_requested.connect(self.on_voice_requested)
        self.hotkey_handler.start()
        
        self.setup_tray()
        self.chat_window.voice_service.status_callback = lambda state, visible: self.hud.voice_signal.emit(state, visible)
        # self.chat_window.voice_service.start_listening_mode()  # Listening starts via shortcut
        
        print("Anders: Aguardando estabilização do hardware...")
        QTimer.singleShot(3000, self._start_delayed_services)

    def _start_delayed_services(self):
        try:
            print("Iniciando Protocolos de Alta Fidelidade...")
            try: self.file_observer.start()
            except Exception as e: print(f"File observer: {e}")
            try: self.log_watcher.start()
            except Exception as e: print(f"Log watcher: {e}")
            try: self.ghost_programmer.start()
            except Exception as e: print(f"Ghost programmer: {e}")
            try: self.crawler.start_background_crawl()
            except Exception as e: print(f"Crawler: {e}")
            try: self.night_watch.start()
            except Exception as e: print(f"Night watch: {e}")
            
            try:
                self.shared_vision.preload()
                print("Visão pre-carregada.")
            except Exception as e: print(f"Erro ao pre-carregar visao: {e}")
            
            try:
                from core.speaker_verification import speaker_verifier
                speaker_verifier.preload()
                speaker_verifier.load_reference()
            except Exception as e: print(f"Erro ao carregar verificador de voz: {e}")
            
            print("Todos os sistemas base operacionais.")
            user_name = os.getenv("USER_NAME", "Senhor")
            self.sound.play_system_sound("Hero")
            self.chat_window.voice_service.speak(f"Sistemas online, {user_name}. Anders carregado.")

            QTimer.singleShot(8000, lambda: self.chat_window.voice_service.start_wake_word_detection(
                callback=self.on_wake_word
            ))
        except Exception as e:
            print(f"Erro ao iniciar servicos tardios: {e}")

    def _update_context_wall(self):
        try:
            file_path = ExecutionService.get_vscode_current_file()
            if file_path and file_path != "unknown":
                data = self.context_aggregator.get_context_for_file(file_path)
                if data: self.hud.context_signal.emit(data)
        except Exception as e: print(f"Erro ao atualizar context wall: {e}")

    def _on_terminal_error(self, payload):
        command = payload.get("command", "")
        exit_code = payload.get("exit_code", "")
        output = payload.get("output", "")
        from core.error_learning import error_learner
        prior_knowledge = error_learner.check_for_prior_errors(command)
        
        prompt = f"O comando {command} falhou (exit {exit_code}). Explique o erro e sugira correção breve.\n{f'Prior: {prior_knowledge}' if prior_knowledge else ''}"
        try:
            suggestion = self.chat_window.llm_client.manager.generate_command(prompt, system_context="TERMINAL_OVERWATCH")
            self.hud.display_signal.emit(f"FALHA NO TERMINAL: {suggestion}", "PROACTIVE", 7000)
            self.chat_window.voice_service.speak(f"Senhor, o comando falhou. {suggestion}")
            error_learner.learn_from_error(command, output, suggestion)
        except Exception as e: print(f"Erro no terminal overwatch: {e}")

    def _apply_ghost_fix(self, file_path, old_text, new_text):
        try:
            content = ExecutionService.read_file(file_path)
            if old_text in content:
                ExecutionService.create_file(file_path, content.replace(old_text, new_text))
                self.hud.display_signal.emit("CORREÇÃO APLICADA", "SUCCESS", 3000)
                self.sound.play_system_sound("Hero")
            else:
                self.hud.display_signal.emit("ERRO: Texto original não encontrado", "LISTENING", 3000)
        except Exception as e: print(f"Erro ao aplicar Ghost Fix: {e}")

    def _ensure_swift_agent(self):
        swift_name = "Omniscient"
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == swift_name: return
            except: continue

        print("Swift Executor não encontrado. Iniciando...")
        bundle_path = resource_path("Omniscient")
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        path = None
        if os.path.exists(bundle_path): path = bundle_path
        elif os.path.exists(os.path.join(project_root, "SwiftAgent/.build/arm64-apple-macosx/release/Omniscient")):
            path = os.path.join(project_root, "SwiftAgent/.build/arm64-apple-macosx/release/Omniscient")

        if path:
            try:
                subprocess.Popen([path], start_new_session=True)
                time.sleep(1)
            except Exception as e: print(f"Erro ao iniciar Swift em {path}: {e}")

    def on_wake_word(self):
        self.hud.display_signal.emit("Ouvindo...", "LISTENING", 0)
        self.hud.voice_signal.emit("LISTENING", True)
        self.sound.play_system_sound("Tink")
        threading.Thread(target=self._listen_after_wake_word, daemon=True).start()

    def _listen_after_wake_word(self):
        try:
            text = self.chat_window.voice_service.listen()
            if text and len(text.strip()) > 1:
                self.hud.display_signal.emit("Processando...", "THINKING", 0)
                self.chat_window.process_silent_command(text)
            else: self.hud.display_signal.emit("Hibernando.", "IDLE", 2000)
        except: self.hud.display_signal.emit("Erro na escuta.", "IDLE", 2000)
        finally: self.hud.voice_signal.emit("LISTENING", False)

    def on_voice_requested(self):
        """Shortcut ⌘ Cmd + Shift Enter.
        Starts a single listening session without wake‑word."""
        # If a voice output is currently playing, stop it
        if self.chat_window.voice_service.is_speaking:
            self.chat_window.voice_service.stop_speaking()
            return
        # Show HUD feedback
        self.hud.display_signal.emit("Escutando...", "LISTENING", 0)
        self.hud.voice_signal.emit("LISTENING", True)
        # Run listening in background thread (apenas single-shot)
        threading.Thread(target=self._listen_after_wake_word, daemon=True).start()

    def _acquire_and_process_command(self):
        self._voice_cycle_active = True
        try:
            while self.chat_window.voice_service.is_continuous_mode:
                while self.chat_window.voice_service.is_speaking: time.sleep(0.1)
                self.hud.voice_signal.emit("LISTENING", True)
                text = self.chat_window.voice_service.listen(continuous_mode=True)
                if text and len(text.strip()) > 1:
                    self._handle_command_cycle(text)
                    time.sleep(0.8)
                else: time.sleep(0.2)
        finally:
            self._voice_cycle_active = False
            self.hud.voice_signal.emit("LISTENING", False)

    def _handle_command_cycle(self, text):
        self.hud.display_signal.emit("Processando...", "THINKING", 0)
        self.hud.voice_signal.emit("THINKING", True)
        
        stop_words = ["chega", "para", "parar", "silêncio", "tchau", "obrigado", "valeu", "encerrar", "quieto"]
        is_stop_request = any(word in text.lower() for word in stop_words)
        self.chat_window.process_silent_command(text)
        
        if is_stop_request: 
            self.hud.voice_signal.emit("IDLE", False)
            return
            
        while getattr(self.chat_window, 'is_processing', False): time.sleep(0.1)
        while self.chat_window.voice_service.is_speaking: time.sleep(0.1)
        
        self.hud.display_signal.emit("Ouvindo... (Contínuo)", "LISTENING", 0)
        self.hud.voice_signal.emit("LISTENING", True)
        follow_up_text = self.chat_window.voice_service.listen(continuous_mode=True)
        if follow_up_text and len(follow_up_text.strip()) > 1: self._handle_command_cycle(follow_up_text)
        else: 
            self.hud.display_signal.emit("Hibernando.", "IDLE", 2000)
            self.hud.voice_signal.emit("IDLE", False)

    def setup_tray(self):
        icon_path = resource_path("src/ui/icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Anders Agent")
        self.chat_window.set_tray_icon(self.tray_icon)
        menu = QMenu()
        # O ChatWindow original é apenas um motor de processamento em fallback agora.
        # menu.addAction("Abrir Chat", self.chat_window.show_and_activate)
        menu.addAction("Sair", self.quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
def main():
    try:
        app = MainApp(sys.argv)
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        crash_log = os.path.expanduser("~/Documents/pessoal/agent/crash_report.txt")
        os.makedirs(os.path.dirname(crash_log), exist_ok=True)
        with open(crash_log, "w") as f:
            f.write(f"ERRO CRÍTICO NA INICIALIZAÇÃO:\n{str(e)}\n\n{traceback.format_exc()}")
        print(f"Erro fatal. Log em: {crash_log}")
        sys.exit(1)

if __name__ == "__main__":
    main()
