import math
import time
import numpy as np
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from core.system_monitor import SystemMonitor

try:
    from AppKit import NSVisualEffectView, NSVisualEffectMaterial, NSVisualEffectState
    HAS_NATIVE_BLUR = True
except ImportError:
    HAS_NATIVE_BLUR = False

class AudioWaveformBar(QWidget):
    """Tarja de áudio animada e compacta."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(180, 28)
        
        self.level = 0.0
        self.target_level = 0.0
        self.is_listening = False
        self.status_text = ""
        self.voice_service = None
        
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate)
        self.anim_timer.start(33)
        
        self.audio_timer = QTimer()
        self.audio_timer.timeout.connect(self._read_audio)
        self.audio_timer.start(50)
        
        self.hide()
    
    def start_monitoring(self, voice_service):
        self.voice_service = voice_service
    
    def _read_audio(self):
        if not self.voice_service or self.voice_service.audio_buffer.empty():
            self.target_level *= 0.8
            return
        try:
            chunk = self.voice_service.audio_buffer.get_nowait()
            audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            energy = min(1.0, np.sqrt(np.mean(audio_np**2)) * 15)
            self.target_level = energy
        except:
            pass
    
    def _animate(self):
        self.level += (self.target_level - self.level) * 0.3
        if self.level > 0.01:
            self.update()
    
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        p.setBrush(QColor(15, 15, 25, 220))
        p.setPen(QPen(QColor(0, 212, 255, 60), 1))
        p.drawRoundedRect(0, 0, self.width(), 18, 6, 6)
        
        bars = 22
        bar_w = 3
        gap = 4
        total = bars * (bar_w + gap)
        start_x = (self.width() - total) // 2
        
        for i in range(bars):
            phase = math.sin(i * 0.4 + time.time() * 4) * 0.5 + 0.5
            h = max(2, int(self.level * 14 * phase))
            
            x = start_x + i * (bar_w + gap)
            y = 9 - h // 2
            
            if self.is_listening:
                c = QColor(255, 59, 48, 180)
            else:
                c = QColor(0, 212, 255, 180)
            
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bar_w, h, 1, 1)
        
        if self.status_text:
            p.setPen(QColor(255, 255, 255, 120))
            p.setFont(QFont("Avenir Next", 7))
            p.drawText(0, 19, self.width(), 9, Qt.AlignmentFlag.AlignCenter, self.status_text)
        
        p.end()
    
    def show_state(self, state="LISTENING"):
        self.is_listening = (state == "LISTENING")
        self.status_text = "gravando..." if state == "LISTENING" else "falando..."
        
        screen = self.screen().geometry()
        self.move(screen.width() - 200, 55)
        self.show()

class HUDOverlay(QWidget):
    # ... (sinais e init seguem iguais)
    display_signal = pyqtSignal(str, str, int) # text, state, duration
    context_signal = pyqtSignal(dict) # dict com file, linear, github
    voice_signal = pyqtSignal(str, bool) # state, visible

    def __init__(self):
        super().__init__()
        self.is_dark = True 
        
        # Timer para esconder o HUD com segurança
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
        # Voice Indicator (AudioWaveformBar)
        self.voice_indicator = AudioWaveformBar()
        
        self.display_signal.connect(self.update_hud)
        self.context_signal.connect(self.update_context_wall)
        self.voice_signal.connect(self._handle_voice_indicator)
        
        self.init_ui()
    
    def connect_voice_service(self, voice_service):
        """Conecta o VoiceService ao indicador de áudio."""
        self.voice_indicator.start_monitoring(voice_service)

    def _handle_voice_indicator(self, state, visible):
        if visible:
            self.voice_indicator.show_state(state)
        else:
            self.voice_indicator.hide()

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
            
        file_name = (data.get('file') or '--')[:15]
        linear_info = (data.get('linear') or '--')[:20]
        github_info = (data.get('github') or '--')[:20]
        
        self.file_label.setText(f"FILE: {file_name}")
        self.linear_label.setText(f"LIN: {linear_info}")
        self.github_label.setText(f"GIT: {github_info}")
        self.context_frame.show()
        self.recenter()
        self.show()

    def recenter(self):
        """Posiciona o HUD no canto superior esquerdo para um visual minimalista."""
        self.move(30, 50)

    def show_message(self, text, duration=3000):
        self.update_hud(text, "IDLE", duration)
