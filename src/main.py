import sys
import os
import re
import threading
import subprocess
import psutil
import time

# Configura o app para rodar apenas como agente de background (sem ícone no Dock)
if sys.platform == "darwin":
    try:
        from AppKit import NSBundle
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info:
            info["LSUIElement"] = "1"
    except ImportError:
        pass

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
from core.sentinela_service import SentinelService
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
        self.recall.vision = shared_vision
        
        # Night Watch (Patrulha Noturna)
        self.night_watch = NightWatch(self.chat_window.llm_client.manager)
        
        # Terminal Overwatch
        self.terminal_overwatch = TerminalOverwatchServer(callback=self._on_terminal_error)
        
        # Context Aggregator
        self.context_aggregator = ContextAggregator()
        self.context_timer = QTimer()
        self.context_timer.timeout.connect(self._update_context_wall)
        self.context_timer.start(10000)
        
        # Sound Service
        self.sound = SoundService()
        
        # Central Watchdog Observer
        from watchdog.observers import Observer
        self.file_observer = Observer()

        # Forge: Asset Manager
        self.asset_manager = AssetManagerService()
        # Auto-Organizer
        self.organizer = AutoOrganizerService(self.chat_window.llm_client)
        # Background Agents
        self.bg_agents = BackgroundAgentService(self)
        
        # Project DNA Crawler: Mapeia exaustivamente os projetos
        self.crawler = ProjectCrawlerService(self.chat_window.llm_client.manager)

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
        
        # Battery Guard (Modo Economico)
        from core.battery_guard import BatteryGuard
        self.battery_guard = BatteryGuard(
            voice_service=self.chat_window.voice_service,
            hud=self.hud
        )
        
        # Deep Focus Service (Pomodoro)
        from core.deep_focus_service import DeepFocusService
        self.deep_focus = DeepFocusService(
            voice_service=self.chat_window.voice_service,
            hud=self.hud
        )
        
        # System Health Monitor
        from core.system_health import SystemHealth
        self.system_health = SystemHealth(hud=self.hud)
        
        # Task Manager
        from core.task_manager import TaskManager
        self.task_manager = TaskManager(llm_client=self.chat_window.llm_client)
        
        # Sentinela Service
        self.sentinela = SentinelService(self.chat_window.voice_service, self.hud)
        
        # Monitor Service
        self.monitor = MonitorService(
            self.chat_window.llm_client, 
            self.chat_window.voice_service,
            self.chat_window.llm_client.memory_client,
            hud=self.hud
        )
        self.monitor.vision = shared_vision
        
        # Timer de Polling para Hotkeys vindas do SwiftAgent
        self.swift_hotkey_timer = QTimer()
        self.swift_hotkey_timer.timeout.connect(self._check_swift_hotkeys)
        self.swift_hotkey_timer.start(100)

        # Tray Icon Setup
        self.setup_tray()
        
        # Configura callback de status de voz
        self.chat_window.voice_service.status_callback = lambda state, visible: self.hud.voice_signal.emit(state, visible)
        self.chat_window.voice_service.start_wake_word_detection(callback=self._on_wake_word)
        
        # Conecta VoiceService ao AudioWaveformBar
        self.hud.connect_voice_service(self.chat_window.voice_service)
        
        self.sound.play_system_sound("Hero")
        user_name = os.getenv("USER_NAME", "Senhor")
        self.chat_window.voice_service.speak(f"Sistemas online, {user_name}.")
        
        print("Omniscient: Sistemas operacionais.")
        QTimer.singleShot(5000, self._start_delayed_services)
        
        # Briefing de inicialização removido conforme solicitado
        # threading.Thread(target=self._run_startup_briefing, daemon=True).start()
        print("Omniscient Agent iniciado e pronto!")

    def _check_swift_hotkeys(self):
        try:
            from core.bridge_service import bridge
            response = bridge.send_sync({"action": "get_events"})
            if response and response.get("status") == "ok":
                events = response.get("events", [])
                for event in events:
                    if event == "hotkey_chat":
                        self.chat_window.show_and_activate()
                    elif event == "hotkey_voice":
                        self.on_voice_requested()
        except Exception:
            pass

    def _start_delayed_services(self):
        def _safe_init():
            try:
                print("🚀 Iniciando Protocolos de Alta Fidelidade (Sequencial)...")
                
                print("   [1/8] Sincronizando Hotkeys Nativas...")
                time.sleep(1.0)
                
                print("   [2/8] Ativando Delta-Vision...")
                self.delta_vision.start()
                time.sleep(1.5)
                
                print("   [3/8] Ativando Sentinela...")
                self.sentinela.start()
                time.sleep(1.0)
                
                print("   [4/8] Ativando Monitor de Sistema...")
                self.monitor.start()
                time.sleep(1.0)
                
                print("   [5/8] Ativando Log Watcher & Ghost Programmer...")
                self.log_watcher.start()
                self.ghost_programmer.start()
                self.file_observer.start()
                time.sleep(1.0)
                
                print("   [6/8] Ativando Project Crawler...")
                self.crawler.start_background_crawl()
                time.sleep(1.0)
                
                print("   [7/8] Ativando Night Watch...")
                self.night_watch.start()
                
                print("   [7.5/8] Ativando Battery Guard...")
                self.battery_guard.start_monitoring()
                
                print("   [8/8] Ativando Auto-Organizer & Background Agents...")
                # Asset Manager e Auto-Organizer compartilham a pasta Downloads
                # Para evitar RuntimeError no Watchdog, agendamos apenas uma vez por path
                self.asset_manager.start(observer=self.file_observer)
                # O organizer só agenda se o path já não estiver sendo monitorado pelo observer ou se usarmos caminhos diferentes
                # No caso atual, vamos apenas garantir que a inicialização não quebre o app
                try:
                    self.organizer.start(observer=self.file_observer)
                except Exception as e:
                    print(f"   Aviso: Auto-Organizer compartilhou observador: {e}")
                
                self.bg_agents.start(observer=self.file_observer)
                
                print("✅ Todos os sistemas operacionais e seguros.")
            except Exception as e:
                print(f"❌ Erro crítico na inicialização sequencial: {e}")

        threading.Thread(target=_safe_init, daemon=True).start()

    def _run_startup_briefing(self):
        print("Preparando briefing proativo...")
        time.sleep(4)
        try:
            cal_events = ExecutionService.get_calendar_events()
            unread_mails = ExecutionService.mail_unread(count=3)
            system_info = ExecutionService.get_system_info()
            
            prompt = f"Gere um briefing de saudação curto e elegante para o JHORDAN. CONTEXTO: {cal_events}, {unread_mails}, {system_info}. Regras: Breve, PT-BR."
            briefing_text = self.chat_window.llm_client.chat([{"role": "user", "content": prompt}])
            
            if briefing_text and "Erro" not in briefing_text:
                self.hud.display_signal.emit("Briefing Matinal", "PROACTIVE", 5000)
                self.chat_window.voice_service.speak(briefing_text)
        except Exception as e:
            print(f"Erro ao gerar briefing proativo: {e}")

    def _update_context_wall(self):
        try:
            file_path = ExecutionService.get_vscode_current_file()
            if file_path and file_path != "unknown":
                data = self.context_aggregator.get_context_for_file(file_path)
                if data:
                    self.hud.context_signal.emit(data)
        except Exception as e:
            print(f"Erro ao atualizar context wall: {e}")

    def _on_terminal_error(self, payload):
        command = payload.get("command", "")
        exit_code = payload.get("exit_code", "")
        output = payload.get("output", "")
        from core.error_learning import error_learner
        prior_knowledge = error_learner.check_for_prior_errors(command)
        prompt = f"JARVIS: Comando {command} falhou ({exit_code}). Explique brevemente."
        try:
            suggestion = self.chat_window.llm_client.manager.generate_command(prompt, system_context="TERMINAL_OVERWATCH")
            self.hud.display_signal.emit(f"FALHA: {suggestion}", "PROACTIVE", 7000)
            self.chat_window.voice_service.speak(f"Senhor, o comando {command.split()[0]} falhou. {suggestion}")
            error_learner.learn_from_error(command, output or f"Exit code {exit_code}", suggestion)
        except Exception as e:
            print(f"Erro ao processar erro do terminal: {e}")

    def _apply_ghost_fix(self, file_path, old_text, new_text):
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
        """Verifica se o binário Swift está rodando, se não, inicia (ou reinicia se for antigo)."""
        swift_name = "Omniscient"
        print(f"--- [STARTUP] Verificando {swift_name} nativo ---")
        
        # Mata qualquer instância órfã ou antiga
        try:
            subprocess.run(["killall", swift_name], capture_output=True)
            time.sleep(0.5)
        except Exception:
            pass

        # Procura o binário
        dev_path_release = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SwiftAgent/.build/arm64-apple-macosx/release/Omniscient")
        bundle_path = resource_path("Omniscient")

        path = bundle_path if os.path.exists(bundle_path) else dev_path_release
        
        if os.path.exists(path):
            print(f"   [Nativo] Executável encontrado em: {path}")
            try:
                # Inicia o processo nativo e captura logs em tempo real
                proc = subprocess.Popen([path], start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                
                def _log_swift():
                    print("   [Nativo] Listener de logs Swift ativo.")
                    for line in iter(proc.stdout.readline, ""):
                        # Repassa logs de debug do Swift para o terminal Python
                        if "DEBUG" in line:
                            print(f"   [Nativo] {line.strip()}")
                
                threading.Thread(target=_log_swift, daemon=True).start()
                time.sleep(2)
                print("   [Nativo] Ponte de comunicação estabelecida.")
            except Exception as e:
                print(f"   [ERRO] Falha ao iniciar binário Swift: {e}")
        else:
            print(f"   [ERRO] Binário nativo NÃO encontrado em: {path}")
            print("   Dica: Rode 'cd SwiftAgent && swift build -c release' primeiro.")

    def on_voice_requested(self):
        if self.chat_window.voice_service.is_speaking:
            self.chat_window.voice_service.stop_speaking()
            return

        is_active = self.chat_window.voice_service.toggle_continuous_mode()
        if is_active:
            self.hud.display_signal.emit("MODO CONTÍNUO: ATIVADO", "LISTENING", 3000)
            self.sound.wake()
            if not getattr(self, "_voice_cycle_active", False):
                threading.Thread(target=self._acquire_and_process_command, daemon=True).start()
        else:
            self.hud.display_signal.emit("MODO CONTÍNUO: DESATIVADO", "IDLE", 3000)
            self.chat_window.voice_service.abort_listen = True
            self.sound.play_system_sound("Tink")

    def _on_wake_word(self):
        """Callback chamado quando wake word é detectada pelo microfone."""
        # Se já está no loop do atalho, não duplica
        if getattr(self, "_voice_cycle_active", False):
            return
        # Tocar som de confirmação ANTES de processar
        from core.sound_service import SoundService
        SoundService.wake()  # Som "Ping"
        # Aguardar 0.5s para o usuário saber que foi ouvido
        time.sleep(0.5)
        def _process():
            self._voice_cycle_active = True
            try:
                self.hud.voice_signal.emit("LISTENING", True)
                text = self.chat_window.voice_service.listen(continuous_mode=True)
                if text and len(text.strip()) > 1:
                    clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
                    wake_words = ["omni", "omniscient", "omniciente", "bagual", "hominy"]
                    falsepositives = ["menino", "harmonia", "dominó", "dominio", "comigo", "combinou"]
                    
                    # Verificar se NÃO é falso positivo
                    is_falsepositive = any(fp in clean for fp in falsepositives)
                    
                    # Wake word deve estar no INÍCIO (primeira palavra)
                    words_clean = clean.split()
                    has_wake = False
                    if not is_falsepositive and words_clean:
                        for kw in wake_words:
                            if words_clean[0] == kw:
                                has_wake = True
                                break
                    
                    if has_wake:
                        # Verificar voiceprint ANTES de processar
                        voice_service = self.chat_window.voice_service
                        if voice_service.voiceprint.is_registered():
                            # Capturar áudio atual para identificação
                            audio_data = None
                            with voice_service.audio_lock:
                                if len(voice_service.wake_word_window) >= voice_service.RATE:
                                    audio_data = np.array(voice_service.wake_word_window, dtype=np.float32)
                            
                            if audio_data is not None:
                                is_user, similarity, label = voice_service.identify_speaker(audio_data)
                                if not is_user:
                                    print(f"Voiceprint: Voz desconhecida (sim={similarity:.2f}). Ignorando.")
                                    return
                        
                        # Remove a wake word do texto antes de enviar ao LLM
                        for kw in wake_words:
                            clean = re.sub(r'\b' + re.escape(kw) + r'\b', '', clean).strip()
                        if clean:
                            print(f"DEBUG WAKE: Comando: '{clean}'")
                            self._handle_command_cycle(clean)
            finally:
                self._voice_cycle_active = False
                self.hud.voice_signal.emit("LISTENING", False)
        threading.Thread(target=_process, daemon=True).start()

    def _acquire_and_process_command(self):
        self._voice_cycle_active = True
        wake_words = ["omni", "omniscient", "omniciente", "bagual", "hominy"]
        falsepositives = ["menino", "harmonia", "dominó", "dominio", "comigo", "combinou"]
        try:
            while self.chat_window.voice_service.is_continuous_mode:
                while self.chat_window.voice_service.is_speaking:
                    time.sleep(0.1)
                self.hud.voice_signal.emit("LISTENING", True)
                text = self.chat_window.voice_service.listen(continuous_mode=True)
                if text and len(text.strip()) > 1:
                    clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
                    words_clean = clean.split()
                    
                    # Verificar se NÃO é falso positivo
                    is_falsepositive = any(fp in clean for fp in falsepositives)
                    
                    # Wake word deve estar no INÍCIO (primeira palavra)
                    has_wake = False
                    if not is_falsepositive and words_clean:
                        for kw in wake_words:
                            if words_clean[0] == kw:
                                has_wake = True
                                break
                    
                    if has_wake:
                        # Verificar voiceprint ANTES de processar
                        voice_service = self.chat_window.voice_service
                        if voice_service.voiceprint.is_registered():
                            # Capturar áudio atual para identificação
                            audio_data = None
                            with voice_service.audio_lock:
                                if len(voice_service.wake_word_window) >= voice_service.RATE:
                                    audio_data = np.array(voice_service.wake_word_window, dtype=np.float32)
                            
                            if audio_data is not None:
                                is_user, similarity, label = voice_service.identify_speaker(audio_data)
                                if not is_user:
                                    print(f"Voiceprint: Voz desconhecida (sim={similarity:.2f}). Ignorando.")
                                    time.sleep(0.2)
                                    continue
                        
                        # Remove a wake word do texto antes de enviar ao LLM
                        for kw in wake_words:
                            clean = re.sub(r'\b' + re.escape(kw) + r'\b', '', clean).strip()
                    else:
                        # Sem wake word explícita = ignorar
                        time.sleep(0.2)
                        continue
                    if not clean:
                        time.sleep(0.2)
                        continue
                    print(f"DEBUG CICLO: Comando final: '{clean}'")
                    self._handle_command_cycle(clean)
                    time.sleep(0.8)
                else:
                    time.sleep(0.2)
        finally:
            self._voice_cycle_active = False
            self.hud.voice_signal.emit("LISTENING", False)

    def _handle_command_cycle(self, text):
        self.hud.display_signal.emit("Processando...", "THINKING", 0)
        self.chat_window.process_silent_command(text)
        while getattr(self.chat_window, 'is_processing', False):
            time.sleep(0.1)
        while self.chat_window.voice_service.is_speaking:
            time.sleep(0.1)

    def setup_tray(self):
        icon_path = resource_path("src/ui/icon.png")
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self) if os.path.exists(icon_path) else QSystemTrayIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon), self)
        self.tray_icon.setToolTip("Omniscient Agent")
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
