from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPainterPath, QLinearGradient
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
    """Equalizador Minimalista de Alta Sensibilidade."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._amp = 0.0
        self._target = 0.0
        self._phase = 0.0
        self._mode = "idle"
        self._color = QColor(255, 255, 255) # Default White
        self.setFixedSize(160, 32)

    def set_amplitude(self, value: float):
        # Sensibilidade aumentada
        self._target = max(0.01, min(1.0, value * 6.0))

    def set_mode(self, state: str):
        self._mode = state.lower()
        if self._mode == "listening":
            self._color = QColor(255, 255, 255, 255) # Branco Puro
        elif self._mode == "speaking":
            self._color = QColor(255, 59, 48, 255)   # Vermelho Vibrante
        elif self._mode in ["thinking", "processing"]:
            self._color = QColor(255, 214, 10, 255)  # Amarelo Apple
        else:
            self._color = QColor(255, 255, 255, 100)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self._amp += (self._target - self._amp) * 0.3
        self._phase += 0.15 + (self._amp * 0.25)

        w, h = self.width(), self.height()
        cy = h / 2

        if self._mode in ["thinking", "processing"]:
            # Linha amarela esticada e estática (com glow)
            bar_w = w - 20
            bar_h = 3
            x = (w - bar_w) / 2
            y = cy - bar_h / 2
            
            # Glow Effect
            glow = QColor(self._color)
            glow.setAlpha(100)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawRoundedRect(QRectF(x-2, y-2, bar_w+4, bar_h+4), 4, 4)
            
            p.setBrush(QBrush(self._color))
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.5, 1.5)
        else:
            # Wave reativa
            n = 15
            bar_w = 3
            gap = 4
            total = n * bar_w + (n - 1) * gap
            cx = (w - total) / 2

            for i in range(n):
                x = cx + i * (bar_w + gap)
                idle = 2 + 3 * abs(math.sin(self._phase + i * 0.3))
                reactivity = 1.0 - (abs(i - (n/2)) * 0.12)
                bar_h = idle + (self._amp * (h - 4) * reactivity)
                y = cy - bar_h / 2

                color = QColor(self._color)
                alpha = int(180 + 75 * self._amp)
                color.setAlpha(min(255, alpha))
                
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(color))
                p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w/2, bar_w/2)
        p.end()


class VoiceOverlay(QWidget):
    """Container vertical persistente e Click-Through."""

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        # ToolTip + StaysOnTop garante persistência no macOS sem roubar foco
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
        # 100% Click-Through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setFixedWidth(220)
        self.setFixedHeight(140)
        self._position()

    def _position(self):
        screen = self.screen().geometry()
        # Fixa 20px da borda direita e topo
        self.move(screen.width() - self.width() - 20, 20)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(8)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Container Principal com Blur
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("OverlayBG")
        self.bg_frame.setStyleSheet("""
            #OverlayBG {
                background-color: rgba(0, 0, 0, 0.85);
                border: 0.5px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(12, 12, 12, 12)
        bg_layout.setSpacing(10)

        # 1. Wave
        self.wave = SiriWaveWidget()
        bg_layout.addWidget(self.wave, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 2. Status Label (Opcional, discreto)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 9px; font-weight: 600; text-transform: uppercase;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_layout.addWidget(self.status_label)

        # 3. Tags Container
        self.tags_container = QFrame()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(4)
        bg_layout.addWidget(self.tags_container)
        
        self.main_layout.addWidget(self.bg_frame)
        self.bg_frame.hide()

    def set_state(self, state: str):
        self.wave.set_mode(state)
        self.status_label.setText(state.replace("_", " "))
        
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
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px; font-weight: 500; background: transparent;")
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
