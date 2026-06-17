from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPainterPath, QPen, QLinearGradient
import math

try:
    from AppKit import (
        NSVisualEffectView, NSVisualEffectMaterial, NSVisualEffectState,
        NSVisualEffectBlendingMode,
        NSViewWidthSizable, NSViewHeightSizable
    )
    import objc
    from ctypes import c_void_p
    HAS_NATIVE_BLUR = True
except ImportError:
    HAS_NATIVE_BLUR = False


class SiriWaveWidget(QWidget):
    """Equalizador de Linha Contínua (Spline) - Alta Elegância."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._amp = 0.0
        self._target = 0.0
        self._phase = 0.0
        self._mode = "idle"
        self._color = QColor(255, 255, 255)
        self.setFixedSize(200, 40)

    def set_amplitude(self, value: float):
        # Sensibilidade extrema para a linha contínua
        self._target = max(0.01, min(1.0, value * 8.0))

    def set_mode(self, state: str):
        self._mode = state.lower()
        if self._mode == "listening":
            self._color = QColor(255, 255, 255, 255)
        elif self._mode == "speaking":
            self._color = QColor(255, 59, 48, 255)
        elif self._mode in ["thinking", "processing"]:
            self._color = QColor(255, 214, 10, 255)
        else:
            self._color = QColor(255, 255, 255, 100)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self._amp += (self._target - self._amp) * 0.2
        self._phase += 0.2 + (self._amp * 0.3)

        w, h = self.width(), self.height()
        cy = h / 2

        if self._mode in ["thinking", "processing"]:
            # LINHA AMARELA ESTICADA (Glow estático pulsante)
            path = QPainterPath()
            path.moveTo(10, cy)
            path.lineTo(w - 10, cy)
            
            # Glow
            pen_glow = QPen(self._color, 4)
            glow_c = QColor(self._color)
            glow_c.setAlpha(80)
            pen_glow.setColor(glow_c)
            p.setPen(pen_glow)
            p.drawPath(path)
            
            # Linha principal
            p.setPen(QPen(self._color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(path)
        else:
            # WAVE SENOIDAL DINÂMICA
            path = QPainterPath()
            path.moveTo(0, cy)
            
            points = 40
            dx = w / points
            
            for i in range(points + 1):
                x = i * dx
                # Envelope gaussiano para suavizar as pontas
                envelope = math.exp(-0.5 * ((i - points/2) / (points/4))**2)
                
                # Frequência baseada no modo
                freq = 0.5 if self._mode == "speaking" else 0.8
                
                y = cy + (self._amp * 15 * envelope * math.sin(self._phase + i * freq))
                path.lineTo(x, y)

            # Desenha com gradiente sutil
            pen = QPen(self._color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawPath(path)
            
            # Segunda camada mais fina para brilho
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.drawPath(path)
            
        p.end()


class VoiceOverlay(QWidget):
    """Container vertical unificado com largura fixa de 240px."""

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # LARGURA UNIFICADA: 240px
        self.setFixedWidth(240)
        self.setFixedHeight(160)
        self._position()

    def _position(self):
        screen = self.screen().geometry()
        # 20px de margem (Sincronizado com HUD)
        self.move(screen.width() - self.width() - 20, 20)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("OverlayBG")
        # Estilo Apple Glass mais slim
        self.bg_frame.setStyleSheet("""
            #OverlayBG {
                background-color: rgba(15, 15, 20, 0.82);
                border: 0.5px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(12, 10, 12, 10)
        bg_layout.setSpacing(6)

        # 1. Wave
        self.wave = SiriWaveWidget()
        bg_layout.addWidget(self.wave, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 2. Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_layout.addWidget(self.status_label)

        # 3. Tags (Contexto)
        self.tags_container = QFrame()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(4, 4, 4, 4)
        self.tags_layout.setSpacing(3)
        bg_layout.addWidget(self.tags_container)
        
        self.main_layout.addWidget(self.bg_frame)
        self.bg_frame.hide()

    def set_state(self, state: str):
        self.wave.set_mode(state)
        self.status_label.setText(state.upper())
        
        if state in ["listening", "speaking", "thinking", "processing"]:
            self.bg_frame.show()
            self.show()
            self.raise_()
        else:
            QTimer.singleShot(2000, self.bg_frame.hide)

    def update_context(self, file_lbl, task_lbl, repo_lbl):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)
            
        for lbl in [file_lbl, task_lbl, repo_lbl]:
            # Força fonte mono e elide para não quebrar largura
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 10px; font-family: 'Menlo'; background: transparent;")
            lbl.setFixedWidth(210) # Garante que cabe nos 240px
            self.tags_layout.addWidget(lbl)
        
        self.bg_frame.show()
        self.show()
        self.raise_()

    def set_amplitude(self, value: float):
        self.wave.set_amplitude(value)

    def _tick(self):
        self.wave.update()

    def show(self):
        super().show()
        self.raise_()
        if not hasattr(self, '_blur_applied'):
            self._blur_applied = True
            QTimer.singleShot(50, self._apply_blur)

    def _apply_blur(self):
        if not HAS_NATIVE_BLUR: return
        try:
            win_id = self.winId()
            ns_view = objc.objc_object(c_void_p=win_id.__int__())
            effect = NSVisualEffectView.new()
            effect.setMaterial_(NSVisualEffectMaterial.HUDWindow)
            effect.setBlendingMode_(NSVisualEffectBlendingMode.BehindWindow)
            effect.setFrame_(ns_view.bounds())
            effect.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            ns_view.addSubview_positioned_relativeTo_(effect, -1, None)
        except: pass
