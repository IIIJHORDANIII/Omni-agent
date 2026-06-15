from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPoint
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QPainterPath, QLinearGradient
from core.system_monitor import SystemMonitor
from ui.voice_overlay import VoiceOverlay
import sys

# Tenta importar as bibliotecas nativas do macOS para o efeito de Glass/Vibrancy
try:
    from AppKit import (
        NSVisualEffectView, NSVisualEffectMaterial, NSVisualEffectState,
        NSViewWidthSizable, NSViewHeightSizable, NSApp, NSAppearance,
        NSWindow, NSColor, NSBezierPath, NSMakeRect
    )
    import objc
    from ctypes import c_void_p
    HAS_NATIVE_BLUR = True
except ImportError:
    HAS_NATIVE_BLUR = False


def _tahoe_style(bg="rgba(30, 30, 38, 0.55)", border="rgba(255, 255, 255, 0.08)", radius=18):
    return f"""
        QFrame {{
            background-color: {bg};
            border: 0.5px solid {border};
            border-radius: {radius}px;
        }}
    """


class HUDOverlay(QWidget):
    display_signal = pyqtSignal(str, str, int)
    context_signal = pyqtSignal(dict)
    voice_signal = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.is_dark = True
        self._visible = False

        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

        self.voice_overlay = VoiceOverlay()

        self.display_signal.connect(self.update_hud)
        self.context_signal.connect(self.update_context_wall)
        self.voice_signal.connect(self._handle_voice_overlay)

        self._init_ui()

    def _handle_voice_overlay(self, state, visible):
        if visible:
            self.voice_overlay.set_state(state.lower())
        else:
            self.voice_overlay.set_state("idle")

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Container principal — glass Tahoe
        self.container = QFrame()
        self.container.setObjectName("HudContainer")
        self.container.setStyleSheet(_tahoe_style())

        if HAS_NATIVE_BLUR:
            self._apply_vibrancy(self.container)

        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(18, 14, 18, 14)
        inner.setSpacing(10)

        # Linha superior: status + label
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.status_dot = QFrame()
        self.status_dot.setFixedSize(8, 8)
        self._set_dot_color("#30d158")

        self.label = QLabel("Omniscient Operacional")
        self.label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.92);
                font-size: 12px;
                font-family: '.AppleSystemUIFont', 'Helvetica Neue', -apple-system, sans-serif;
                font-weight: 600;
                letter-spacing: 0.2px;
            }
        """)

        top_row.addWidget(self.status_dot)
        top_row.addWidget(self.label)
        top_row.addStretch()

        # Painel de contexto — sutil
        self.context_frame = QFrame()
        self.context_frame.setStyleSheet(_tahoe_style(
            bg="rgba(255, 255, 255, 0.03)",
            border="rgba(255, 255, 255, 0.04)",
            radius=12
        ))
        ctx_inner = QVBoxLayout(self.context_frame)
        ctx_inner.setContentsMargins(14, 10, 14, 10)
        ctx_inner.setSpacing(4)

        self.file_label = self._make_context_label()
        self.linear_label = self._make_context_label()
        self.github_label = self._make_context_label()

        for lbl in [self.file_label, self.linear_label, self.github_label]:
            ctx_inner.addWidget(lbl)

        self.context_frame.hide()

        inner.addLayout(top_row)
        inner.addWidget(self.context_frame)

        self.main_layout.addWidget(self.container)
        self.hide()

    def _make_context_label(self):
        lbl = QLabel("--")
        lbl.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.45);
                font-size: 10px;
                font-family: 'SF Mono', 'Menlo', monospace;
                font-weight: 400;
                letter-spacing: 0.3px;
                border: none;
                background: transparent;
            }
        """)
        return lbl

    def _set_dot_color(self, hex_color: str):
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                background-color: {hex_color};
                border-radius: 4px;
                border: none;
            }}
        """)

    def _apply_vibrancy(self, widget):
        """Aplica NSVisualEffectView nativo do macOS como fundo vibrancy."""
        try:
            win_id = widget.winId()
            if win_id is None:
                QTimer.singleShot(100, lambda: self._apply_vibrancy(widget))
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
            self._vibrancy_view = effect
        except Exception:
            pass

    def update_hud(self, text, state="IDLE", duration=3000):
        self.hide_timer.stop()

        self.label.setText(text)

        state_colors = {
            "IDLE": "#30d158",
            "LISTENING": "#ff453a",
            "THINKING": "#ffd60a",
            "PROACTIVE": "#64d2ff",
            "SUCCESS": "#30d158",
            "CODING": "#bf5af2",
        }
        color = state_colors.get(state, "#30d158")
        self._set_dot_color(color)

        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._visible = True

        if duration > 0:
            self.hide_timer.start(duration)

    def update_context_wall(self, data):
        if not data:
            self.context_frame.hide()
            return

        self.file_label.setText(f"FILE  {data.get('file', '--')[:28]}")
        self.linear_label.setText(f"TASK  {data.get('linear', '--')[:28]}")
        self.github_label.setText(f"REPO  {data.get('github', '--')[:28]}")
        self.context_frame.show()
        self._reposition()
        self.show()

    def _reposition(self):
        """Posiciona o HUD no canto superior direito, estilo Tahoe."""
        screen = self.screen().geometry()
        self.adjustSize()
        w = self.width()
        x = screen.width() - w - 24
        y = 52
        self.move(x, y)

    def _fade_out(self):
        self._visible = False
        self.hide()

    def show_message(self, text, duration=3000):
        self.update_hud(text, "IDLE", duration)
