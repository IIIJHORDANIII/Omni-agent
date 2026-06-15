from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from core.system_monitor import SystemMonitor
from ui.voice_overlay import VoiceOverlay
import sys

# Tenta importar as bibliotecas nativas do macOS para o efeito de Glass/Vibrancy
try:
    from AppKit import NSVisualEffectView, NSVisualEffectMaterial, NSVisualEffectState, NSViewWidthSizable, NSViewHeightSizable, NSApp, NSAppearance
    import objc
    from ctypes import c_void_p
    HAS_NATIVE_BLUR = True
except ImportError as e:
    print(f"DEBUG: AppKit/objc import failed: {e}")
    HAS_NATIVE_BLUR = False

class HUDOverlay(QWidget):
    # ... (sinais e init seguem iguais)
    display_signal = pyqtSignal(str, str, int) # text, state, duration
    context_signal = pyqtSignal(dict) # dict com file, linear, github
    voice_signal = pyqtSignal(str, bool) # state, visible

    def __init__(self):
        super().__init__()
        print(f"DEBUG: HUD init - HAS_NATIVE_BLUR: {HAS_NATIVE_BLUR}")
        self.is_dark = True 
        
        # Timer para esconder o HUD com segurança
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
        # Voice Indicator Popup
        self.voice_overlay = VoiceOverlay()
        
        self.display_signal.connect(self.update_hud)
        self.context_signal.connect(self.update_context_wall)
        self.voice_signal.connect(self._handle_voice_overlay)
        
        self.init_ui()

    def _handle_voice_overlay(self, state, visible):
        if visible:
            self.voice_overlay.set_state(state.lower())
        else:
            self.voice_overlay.set_state("idle")

    def apply_vibrancy(self):
        """Desativado temporariamente para corrigir bug do quadrado preto/blur."""
        return

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # Cores JARVIS
        text_color = "white"
        accent_color = "#00d4ff"
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 10, 20, 10)
        self.main_layout.setSpacing(15)
        
        # --- MENSAGENS (CONTAINER PRINCIPAL - ESTILO VIDRO) ---
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(25, 25, 45, 240), stop:1 rgba(10, 10, 20, 255));
                border: 1px solid rgba(0, 212, 255, 120);
                border-radius: 12px;
                min-width: 250px;
            }}
        """)
        inner_layout = QHBoxLayout(self.container)
        inner_layout.setContentsMargins(20, 10, 25, 10)
        
        # Indicador de Status (Círculo Neon)
        self.indicator = QFrame()
        self.indicator.setFixedSize(10, 10)
        self.indicator.setStyleSheet(f"background-color: {accent_color}; border-radius: 5px; border: 1px solid white;")
        
        self.label = QLabel("OMNISCIENT OPERACIONAL")
        self.label.setStyleSheet(f"color: {text_color}; font-size: 13px; font-family: 'Avenir Next'; font-weight: 800; letter-spacing: 1px; text-transform: uppercase;")
        
        inner_layout.addWidget(self.indicator)
        inner_layout.addSpacing(10)
        inner_layout.addWidget(self.label)
        
        # --- CONTEXTO (PAINEL ROXO) ---
        self.context_frame = QFrame()
        self.context_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(175, 82, 222, 50); 
                border: 1px solid rgba(175, 82, 222, 120); 
                border-radius: 8px;
            }
        """)
        ctx_layout = QVBoxLayout(self.context_frame)
        self.file_label = QLabel("FILE: --")
        self.linear_label = QLabel("LIN: --")
        self.github_label = QLabel("GIT: --")
        for lbl in [self.file_label, self.linear_label, self.github_label]:
            lbl.setStyleSheet("color: #af52de; font-size: 10px; font-weight: bold; border: none; background: transparent;")
            ctx_layout.addWidget(lbl)
        
        # Adiciona ao layout principal
        self.main_layout.addWidget(self.container)
        self.main_layout.addWidget(self.context_frame)
        
        self.context_frame.hide()
        self.hide()
        QTimer.singleShot(200, self.apply_vibrancy)

    def update_hud(self, text, state="IDLE", duration=3000):
        self.hide_timer.stop() # Cancela qualquer fechamento pendente
        
        self.label.setText(text.upper())
        colors = {
            "IDLE": "#00d4ff", "LISTENING": "#ff3b30", "THINKING": "#ffcc00",
            "PROACTIVE": "#4cd964", "SUCCESS": "#34c759", "CODING": "#af52de"
        }
        color = colors.get(state, "#00d4ff")
        
        # Atualiza o brilho neon do indicador e a borda do container
        self.indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: 1px solid white;")
        
        self.container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(25, 25, 45, 240), stop:1 rgba(10, 10, 20, 255));
                border: 2px solid {color}88;
                border-radius: 12px;
                min-width: 250px;
            }}
        """)
        
        self.adjustSize()
        self.recenter()
        self.show()
        self.raise_()
        
        if duration > 0:
            self.hide_timer.start(duration)

    def update_context_wall(self, data):
        """Atualiza o painel de contexto lateral."""
        if not data:
            self.context_frame.hide()
            return
            
        self.file_label.setText(f"FILE: {data['file'][:15]}...")
        self.linear_label.setText(f"LIN: {data['linear'][:20]}...")
        self.github_label.setText(f"GIT: {data['github'][:20]}...")
        self.context_frame.show()
        self.recenter()
        self.show()

    def recenter(self):
        """Posiciona o HUD no canto superior esquerdo para um visual minimalista."""
        self.move(30, 50)

    def show_message(self, text, duration=3000):
        self.update_hud(text, "IDLE", duration)
