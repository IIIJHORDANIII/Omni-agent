from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QLinearGradient
import math

try:
    from AppKit import (
        NSVisualEffectView, NSVisualEffectMaterial, NSVisualEffectState,
        NSViewWidthSizable, NSViewHeightSizable
    )
    import objc
    from ctypes import c_void_p
    HAS_NATIVE_BLUR = True
except ImportError:
    HAS_NATIVE_BLUR = False


class SiriWaveWidget(QWidget):
    """Barras de onda minimalistas — 4 barras finas estilo Siri."""

    def __init__(self, parent=None, num_bars=4):
        super().__init__(parent)
        self.num_bars = num_bars
        self._amp = 0.0
        self._target = 0.0
        self._smooth = 0.10
        self.setFixedSize(100, 28)

    def set_amplitude(self, value: float):
        self._target = max(0.0, min(1.0, value))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._amp += (self._target - self._amp) * self._smooth

        w, h = self.width(), self.height()
        bar_w = 4
        gap = 10
        total = self.num_bars * bar_w + (self.num_bars - 1) * gap
        cx = (w - total) / 2
        cy = h / 2

        for i in range(self.num_bars):
            x = cx + i * (bar_w + gap)
            phase = i * 1.0 + (self._amp * 2.2)
            bar_h = 3 + (self._amp * (h - 6) * (0.35 + 0.65 * abs(math.sin(phase))))
            y = cy - bar_h / 2

            alpha = int(90 + 140 * self._amp)
            color = QColor(255, 255, 255, alpha)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 2, 2)

        p.end()


class VoiceOverlay(QWidget):
    """Overlay de voz estilo macOS Tahoe — glass, canto direito, ondas."""

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
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

        self.setFixedSize(200, 56)
        self._position()

        if HAS_NATIVE_BLUR:
            self._apply_blur()

    def _position(self):
        screen = self.screen().geometry()
        self.move(screen.width() - self.width() - 24, 110)

    def _apply_blur(self):
        try:
            win_id = self.winId()
            if win_id is None:
                return
            ns_view = objc.objc_object(c_void_p=win_id.__int__())
            effect = NSVisualEffectView.new()
            effect.setMaterial_(NSVisualEffectMaterial.HUDWindow)
            effect.setState_(NSVisualEffectState.Active)
            effect.setBlendingMode_(1)
            effect.setFrame_(ns_view.bounds())
            effect.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            if hasattr(ns_view, 'contentView'):
                ns_view.contentView().addSubview_positioned_relativeTo_(effect, 0, None)
            else:
                ns_view.addSubview_(effect)
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 38, 0.55);
                border: 0.5px solid rgba(255, 255, 255, 0.08);
                border-radius: 18px;
            }
        """)

        inner = QHBoxLayout(self.container)
        inner.setContentsMargins(18, 0, 18, 0)
        inner.setSpacing(12)

        # Status dot
        self.dot = QFrame()
        self.dot.setFixedSize(6, 6)
        self._set_dot("#30d158")

        # Label
        self.label = QLabel("Ouvindo...")
        self.label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 11px;
                font-family: '.AppleSystemUIFont', 'Helvetica Neue', -apple-system, sans-serif;
                font-weight: 500;
                letter-spacing: 0.3px;
            }
        """)

        # Ondas
        self.wave = SiriWaveWidget(num_bars=4)

        inner.addWidget(self.dot)
        inner.addWidget(self.label)
        inner.addStretch()
        inner.addWidget(self.wave)

        layout.addWidget(self.container)

    def _set_dot(self, color: str):
        self.dot.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 3px;
                border: none;
            }}
        """)

    def set_state(self, state: str):
        states = {
            "listening": ("Ouvindo...", "#ff453a"),
            "speaking": ("Falando...", "#64d2ff"),
            "thinking": ("Pensando...", "#ffd60a"),
            "idle": ("", "#30d158"),
        }
        text, dot_color = states.get(state, states["idle"])
        self.label.setText(text)
        self._set_dot(dot_color)

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
        self.wave.set_amplitude(value)

    def _tick(self):
        self.wave.update()
        if self._fading:
            self._opacity -= 0.05
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
