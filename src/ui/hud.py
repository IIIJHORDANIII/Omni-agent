from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from core.system_monitor import SystemMonitor
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

class VoiceIndicator(QWidget):
    """Círculo no canto superior direito para indicação de voz/fala."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(100, 100)
        
        layout = QVBoxLayout(self)
        self.circle = QFrame()
        self.circle.setFixedSize(40, 40)
        # Estilo JARVIS: Brilho externo e borda neon
        self.circle.setStyleSheet("""
            background-color: rgba(0, 212, 255, 30);
            border: 2px solid #00d4ff;
            border-radius: 20px;
        """)
        layout.addWidget(self.circle, alignment=Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def show_state(self, state="LISTENING"):
        colors = {
            "LISTENING": "rgba(255, 59, 48, 100)", # Vermelho suave
            "SPEAKING": "rgba(0, 212, 255, 100)"   # Azul suave
        }
        border_colors = {"LISTENING": "#ff3b30", "SPEAKING": "#00d4ff"}
        
        color = colors.get(state, "rgba(0, 212, 255, 100)")
        border = border_colors.get(state, "#00d4ff")
        
        self.circle.setStyleSheet(f"""
            background-color: {color};
            border: 3px solid {border};
            border-radius: 20px;
        """)
        
        # Posiciona no canto superior direito com margem
        screen = self.screen().geometry()
        self.move(screen.width() - 120, 60)
        self.show()

class HUDOverlay(QWidget):
    # ... (sinais e init seguem iguais)
    display_signal = pyqtSignal(str, str, int) # text, state, duration
    context_signal = pyqtSignal(dict) # dict com file, linear, github
    voice_signal = pyqtSignal(str, bool) # state, visible

    def __init__(self):
        super().__init__()
        print(f"DEBUG: HUD init - HAS_NATIVE_BLUR: {HAS_NATIVE_BLUR}")
        self.is_dark = True 
        
        # Voice Indicator Popup
        self.voice_indicator = VoiceIndicator()
        
        self.display_signal.connect(self.update_hud)
        self.context_signal.connect(self.update_context_wall)
        self.voice_signal.connect(self._handle_voice_indicator)
        
        self.init_ui()
        
        # Timer para telemetria
        self.telemetry_timer = QTimer()
        self.telemetry_timer.timeout.connect(self.update_telemetry)
        self.telemetry_timer.start(5000)

    def _handle_voice_indicator(self, state, visible):
        if visible:
            self.voice_indicator.show_state(state)
        else:
            self.voice_indicator.hide()

    def apply_vibrancy(self):
        """Aplica o efeito de vidro/blur nativo do macOS."""
        if not HAS_NATIVE_BLUR: return

        try:
            view_id = self.winId()
            native_view = objc.objc_object(c_void_p=int(view_id))
            window = native_view.window()
            if window:
                window.setOpaque_(False)
                window.setBackgroundColor_(objc.lookUpClass('NSColor').clearColor())
                # Força o conteúdo a aparecer sobre o blur
                window.setHasShadow_(True)

            effect_view = NSVisualEffectView.alloc().init()
            effect_view.setFrame_(((0, 0), (self.width(), self.height())))
            effect_view.setMaterial_(2) # Dark
            effect_view.setState_(1)
            effect_view.setBlendingMode_(0)
            effect_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            native_view.addSubview_positioned_relativeTo_(effect_view, -1, None)
        except Exception as e:
            print(f"Erro ao aplicar efeito de vidro: {e}")

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Cores JARVIS
        text_color = "white"
        accent_color = "#00d4ff"
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 10, 15, 10)
        self.main_layout.setSpacing(20)
        
        # --- TELEMETRIA ---
        self.telemetry_frame = QFrame()
        self.telemetry_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(10, 10, 15, 230); 
                border: 1px solid {accent_color}88; 
                border-radius: 10px;
            }}
        """)
        tel_layout = QVBoxLayout(self.telemetry_frame)
        self.cpu_label = QLabel("CPU: --%")
        self.ram_label = QLabel("RAM: --%")
        self.bat_label = QLabel("BAT: --%")
        for lbl in [self.cpu_label, self.ram_label, self.bat_label]:
            lbl.setStyleSheet(f"color: {accent_color}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            tel_layout.addWidget(lbl)
            
        # --- MENSAGENS (CONTAINER PRINCIPAL) ---
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(10, 10, 15, 230); 
                border: 2px solid {accent_color}; 
                border-radius: 20px;
            }}
        """)
        inner_layout = QHBoxLayout(self.container)
        self.indicator = QFrame()
        self.indicator.setFixedSize(12, 12)
        self.indicator.setStyleSheet(f"background-color: {accent_color}; border-radius: 6px; border: none;")
        self.label = QLabel("Sistemas Online")
        self.label.setStyleSheet(f"color: {text_color}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        
        inner_layout.addWidget(self.indicator)
        inner_layout.addWidget(self.label)
        inner_layout.setContentsMargins(15, 5, 20, 5)
        
        # --- CONTEXTO ---
        self.context_frame = QFrame()
        self.context_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 10, 15, 230); 
                border: 1px solid #af52de88; 
                border-radius: 10px;
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
        self.main_layout.addWidget(self.telemetry_frame)
        self.main_layout.addWidget(self.container)
        self.main_layout.addWidget(self.context_frame)
        
        self.context_frame.hide()
        self.hide()
        QTimer.singleShot(200, self.apply_vibrancy)

    def update_telemetry(self):
        usage = SystemMonitor.get_resource_usage()
        self.cpu_label.setText(f"CPU: {usage['cpu']}%")
        self.ram_label.setText(f"RAM: {usage['memory']}%")
        self.bat_label.setText(f"BAT: {usage['battery']['percent']}%")
        
        if usage['cpu'] > 80:
            self.cpu_label.setStyleSheet("color: #ff3b30; font-size: 11px; font-weight: 800; border: none; background: transparent;")
        else:
            self.cpu_label.setStyleSheet(f"color: #00d4ff; font-size: 11px; font-weight: 800; border: none; background: transparent;")

    def update_hud(self, text, state="IDLE", duration=3000):
        self.label.setText(text)
        colors = {
            "IDLE": "#00d4ff", "LISTENING": "#ff3b30", "THINKING": "#ffcc00",
            "PROACTIVE": "#4cd964", "SUCCESS": "#34c759", "CODING": "#af52de"
        }
        color = colors.get(state, "#00d4ff")
        self.indicator.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: none;")
        
        # Força o background opaco o suficiente para aparecer sobre o blur
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(20, 20, 25, 240); 
                border: 2px solid {color}; 
                border-radius: 20px;
            }}
        """)
        
        self.adjustSize()
        self.recenter()
        self.show()
        if duration > 0: QTimer.singleShot(duration, self.hide)

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
        screen = self.screen().geometry()
        self.move((screen.width() - self.width()) // 2, 50)

    def show_message(self, text, duration=3000):
        self.update_hud(text, "IDLE", duration)
