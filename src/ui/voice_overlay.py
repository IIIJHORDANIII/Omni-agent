from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont
import math

# Tenta importar NSVisualEffectView para blur nativo do macOS
try:
    from AppKit import NSVisualEffectView, NSVisualEffectMaterial, NSVisualEffectState
    import objc
    HAS_NATIVE_BLUR = True
except ImportError:
    HAS_NATIVE_BLUR = False


class SiriWaveWidget(QWidget):
    """Widget minimalista que desenha ondas estilo Siri com 3 barras finas."""
    
    def __init__(self, parent=None, num_bars=3):
        super().__init__(parent)
        self.num_bars = num_bars
        self._amplitude = 0.0
        self._target = 0.0
        self._smooth = 0.12
        self.setFixedSize(120, 36)
        
    def set_amplitude(self, value: float):
        self._target = max(0.0, min(1.0, value))
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self._amplitude += (self._target - self._amplitude) * self._smooth
        
        w = self.width()
        h = self.height()
        bar_w = 6
        gap = 14
        total = self.num_bars * bar_w + (self.num_bars - 1) * gap
        start_x = (w - total) / 2
        center_y = h / 2
        
        for i in range(self.num_bars):
            x = start_x + i * (bar_w + gap)
            
            # Altura varia com sinusoidal e amplitude
            phase = i * 1.2 + (self._amplitude * 2.5)
            base_h = 4
            max_h = h - 8
            bar_h = base_h + (self._amplitude * max_h * (0.4 + 0.6 * abs(math.sin(phase))))
            
            y = center_y - bar_h / 2
            
            # Cor: branco/azul muito claro, opacidade baseada na amplitude
            alpha = int(80 + 160 * self._amplitude)
            color = QColor(255, 255, 255, alpha)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRect(int(x), int(y), int(bar_w), int(bar_h)), 3, 3)
        
        painter.end()


class VoiceOverlay(QWidget):
    """Overlay minimalista estilo Siri para indicar escuta de voz."""
    
    def __init__(self):
        super().__init__()
        self._amplitude = 0.0
        self._timer = QTimer()
        self._timer.timeout.connect(self._update)
        self._timer.start(25)
        
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        
        self._opacity = 1.0
        self._fading = False
        
        self._setup_window()
        self._setup_ui()
        
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        screen = self.screen().geometry()
        self.setFixedSize(240, 70)
        self.move((screen.width() - self.width()) // 2, 60)
        
        if HAS_NATIVE_BLUR:
            self._apply_blur()
            
    def _apply_blur(self):
        try:
            ns_view = objc.objc_object(c_void_p=self.winId().__int__())
            effect = NSVisualEffectView.new()
            effect.setMaterial_(NSVisualEffectMaterial.HUDWindow)
            effect.setState_(NSVisualEffectState.Active)
            effect.setBlendingMode_(1)
            effect.setFrame_(ns_view.bounds())
            if hasattr(ns_view, 'contentView'):
                ns_view.contentView().addSubview_positioned_relativeTo_(effect, 0, None)
            else:
                ns_view.addSubview_(effect)
            self._blur_view = effect
        except Exception:
            pass
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 28, 35, 0.55);
                border: 0.5px solid rgba(255, 255, 255, 0.08);
                border-radius: 35px;
            }
        """)
        
        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(24, 8, 24, 10)
        inner.setSpacing(4)
        
        self.label = QLabel("Ouvindo...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.75);
                font-size: 11px;
                font-family: 'SF Pro', 'Helvetica Neue', 'Arial', sans-serif;
                font-weight: 400;
                letter-spacing: 0.8px;
            }
        """)
        inner.addWidget(self.label)
        
        self.wave = SiriWaveWidget(num_bars=3)
        inner.addWidget(self.wave, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.container)
        
    def set_state(self, state: str):
        texts = {
            "listening": "Ouvindo...",
            "speaking": "Falando...",
            "thinking": "Pensando...",
            "idle": "",
        }
        self.label.setText(texts.get(state, ""))
        
        if state == "idle":
            self._hide_timer.start(1200)
        else:
            self._hide_timer.stop()
            self._fading = False
            self._opacity = 1.0
            self.setWindowOpacity(1.0)
            self.show()
            self.raise_()
            
    def set_amplitude(self, value: float):
        self._amplitude = value
        self.wave.set_amplitude(value)
        
    def _update(self):
        self.wave.update()
        if self._fading:
            self._opacity -= 0.06
            if self._opacity <= 0:
                self._opacity = 0
                self.hide()
                self._fading = False
            self.setWindowOpacity(self._opacity)
            
    def _fade_out(self):
        self._fading = True
        
    def show(self):
        super().show()
        self._fading = False
        self._opacity = 1.0
        self.setWindowOpacity(1.0)
        self.raise_()
