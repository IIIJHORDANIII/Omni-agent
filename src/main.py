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

class OmniscientAgent(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)
        
        # Hardware Setup: Ajusta Microfone Interno (85% evita distorção/clipping)
        print("Sintonizando hardware de áudio...")
        HardwareManager.set_internal_mic_as_default()
        HardwareManager.set_input_volume(85)
        
        # Garante que o SwiftAgent esteja rodando
        self._ensure_swift_agent()
        
        # UI Components
        self.hud = HUDOverlay()
        self.chat_window = ChatWindow()
        self.ghost_popup = GhostPopup()
        self.ghost_popup.applied.connect(self._apply_ghost_fix)
        
        # Referência compartilhada do VisionService (evita múltiplos carregamentos)
        shared_vision = self.chat_window.llm_client.vision_service
        
        # Recall Service (Memória Fotográfica)
        self.recall = RecallService(self.chat_window.llm_client.manager)
        self.recall.vision = shared_vision # Injeta a instância única
        self.recall.start()
        
        # Night Watch (Patrulha Noturna)
        self.night_watch = NightWatch(self.chat_window.llm_client.manager)
        
        # Terminal Overwatch
        self.terminal_overwatch = TerminalOverwatchServer(callback=self._on_terminal_error)
        self.terminal_overwatch.start()
        
        # Context Aggregator
        self.context_aggregator = ContextAggregator()
        self.context_timer = QTimer()
        self.context_timer.timeout.connect(self._update_context_wall)
        self.context_timer.start(10000) # Atualiza contexto a cada 10s
        
        # Sound Service
        self.sound = SoundService()
        
        # Forge: Asset Manager
        self.asset_manager = AssetManagerService()
        self.asset_manager.start()
        
        # Auto-Organizer: Monitora e organiza downloads via IA
        self.organizer = AutoOrganizerService(self.chat_window.llm_client)
        self.organizer.start()
        
        # Overwatch: Log Watcher & Ghost Programmer
        self.log_watcher = LogWatcherService(
            self.chat_window.llm_client.manager,
            self.chat_window.voice_service,
            self.hud
        )
        self.log_watcher.start()
        
        self.ghost_programmer = GhostPairProgrammer(
            self.chat_window.llm_client.manager,
            self.chat_window.voice_service,
            self.hud
        )
        self.ghost_programmer.fix_suggested.connect(self.ghost_popup.show_suggestion)
        self.ghost_programmer.start()
        
        # Briefing Service
        self.briefing = BriefingService(self.chat_window.llm_client.manager)
        
        # Services
        # O Monitor Service analisa a tela periodicamente em busca de eventos importantes
        # Agora passamos as dependências corretas (LLM, Voz e Memória)
        self.monitor = MonitorService(
            self.chat_window.llm_client, 
            self.voice_service_alias if hasattr(self, 'voice_service_alias') else self.chat_window.voice_service,
            self.chat_window.llm_client.memory_client,
            hud=self.hud
        )
        self.monitor.vision = shared_vision # Injeta a instância única
        self.monitor.start()
        
        # Hotkey Handler (Cmd+Shift+O)
        self.hotkey_handler = GlobalHotkeyHandler()
        self.hotkey_handler.hotkey_pressed.connect(self.chat_window.show_and_activate)
        self.hotkey_handler.start()
        
        # Tray Icon Setup
        self.setup_tray()
        
        # Configura callback de status de voz para o HUD
        self.chat_window.voice_service.status_callback = lambda state, visible: self.hud.voice_signal.emit(state, visible)
        
        # Inicia a Wake Word (Ouvindo por "Desk" ou "Omini")
        self.chat_window.voice_service.start_wake_word_detection(
            self.on_wake_word
        )
        
        # Sequência de inicialização silenciosa (Saudação via Briefing Service apenas)
        self.sound.play_system_sound("Hero")
        
        # Briefing opcional no startup (Saudação baseada na hora)
        threading.Thread(target=self._run_startup_briefing, daemon=True).start()
        
        print("Omniscient Agent iniciado e pronto!")

    def _run_startup_briefing(self):
        """Gera e fala o briefing matinal."""
        try:
            import mlx.core as mx
            # Garante inicialização do MLX na thread via context manager
            with mx.stream(mx.gpu):
                briefing_text = self.briefing.generate_morning_briefing()
                self.chat_window.voice_service.speak(briefing_text)
        except Exception as e:
            print(f"Erro no briefing: {e}")

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
        """Chamado quando um comando no terminal falha."""
        command = payload.get("command", "")
        exit_code = payload.get("exit_code", "")
        
        prompt = f"""Você é o JARVIS. O usuário executou um comando que FALHOU no terminal.
COMANDO: {command}
CÓDIGO DE SAÍDA: {exit_code}

SUA TAREFA:
Explique rapidamente por que falhou e sugira o comando correto para consertar.
Seja extremamente breve (máximo 1 frase).
"""
        try:
            suggestion = self.chat_window.llm_client.manager.generate_command(prompt, system_context="TERMINAL_OVERWATCH")
            self.hud.display_signal.emit(f"FALHA NO TERMINAL: {suggestion}", "PROACTIVE", 7000)
            self.chat_window.voice_service.speak(f"Senhor, o comando {command.split()[0]} falhou. {suggestion}")
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
        dev_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SwiftAgent/.build/arm64-apple-macosx/debug/Omniscient")

        path = bundle_path if os.path.exists(bundle_path) else dev_path

        if os.path.exists(path):
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

    def on_wake_word(self):
        """Chamado quando detecta uma palavra de ativação."""
        self.chat_window.voice_service.stop_speaking() # Interrompe o JARVIS para ouvir o usuário
        self.sound.wake()
        # Som 'PAM' e indicador visual de gravação
        self.sound.play_voice_start()
        self.hud.voice_signal.emit("LISTENING", True)
        
        threading.Thread(target=self._acquire_and_process_command, daemon=True).start()

    def _acquire_and_process_command(self):
        # Mostra HUD indicando que está ouvindo
        self.hud.display_signal.emit("Ouvindo...", "LISTENING", 0)
        
        # Escuta o comando do usuário
        text = self.chat_window.voice_service.listen()
        
        # Esconde indicador de voz após ouvir
        self.hud.voice_signal.emit("LISTENING", False)
        
        if text and len(text.strip()) > 1:
            self.hud.display_signal.emit("Processando...", "THINKING", 0)
            print(f"Comando de voz: {text}")
            self.chat_window.process_silent_command(text)
            self.hud.display_signal.emit("Pronto.", "SUCCESS", 2000)
        else:
            self.hud.display_signal.emit("...", "IDLE", 1)
            print("Nenhum comando capturado.")

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
    app = OmniscientAgent(sys.argv)
    sys.exit(app.exec())
