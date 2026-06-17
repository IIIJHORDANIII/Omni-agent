from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont
from ui.voice_overlay import VoiceOverlay

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


def _apple_stylesheet():
    return """
        QFrame#HudContainer {
            background-color: rgba(0, 0, 0, 0.75);
            border: 0.5px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
        }
    """


class HUDOverlay(QWidget):
    display_signal = pyqtSignal(str, str, int)
    context_signal = pyqtSignal(dict)
    voice_signal = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
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
            # Esconde o container principal se estiver ouvindo para priorizar a wave
            if state.lower() == "listening":
                self.container.hide()
        else:
            self.voice_overlay.set_state("idle")
            self.container.show()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip | # Garante persistência no macOS flutuando sobre tudo
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Click-through total

        # LARGURA UNIFICADA: 240px
        self.setFixedWidth(240)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("HudContainer")
        self.container.setStyleSheet(_apple_stylesheet())

        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.status_dot = QFrame()
        self.status_dot.setFixedSize(10, 10)
        self._set_dot_color("#34c759")

        self.label = QLabel("Anders Operacional")
        self.label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.92);
                font-size: 13px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-weight: 600;
            }
        """)

        top_row.addWidget(self.status_dot)
        top_row.addWidget(self.label)
        top_row.addStretch()

        self.context_frame = QFrame()
        self.context_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.04);
                border: 0.5px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        ctx_inner = QVBoxLayout(self.context_frame)
        ctx_inner.setContentsMargins(12, 8, 12, 8)
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
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-weight: 400;
                border: none;
                background: transparent;
            }
        """)
        return lbl

    def _set_dot_color(self, hex_color: str):
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                background-color: {hex_color};
                border-radius: 5px;
                border: none;
            }}
        """)

    def _apply_vibrancy(self, widget):
        if not HAS_NATIVE_BLUR:
            return
        try:
            win_id = widget.winId()
            if win_id is None:
                QTimer.singleShot(100, lambda: self._apply_vibrancy(widget))
                return
            ns_view = objc.objc_object(c_void_p=win_id.__int__())
            effect = NSVisualEffectView.new()
            effect.setMaterial_(NSVisualEffectMaterial.HUDWindow)
            effect.setState_(NSVisualEffectState.FollowsWindowActiveState)
            effect.setBlendingMode_(NSVisualEffectBlendingMode.BehindWindow)
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
            "IDLE": "#34c759",
            "LISTENING": "#ff453a",
            "THINKING": "#ffd60a",
            "PROACTIVE": "#64d2ff",
            "SUCCESS": "#34c759",
            "CODING": "#bf5af2",
            "SPEAKING": "#ff9f0a",
        }
        color = state_colors.get(state, "#34c759")
        self._set_dot_color(color)

        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._visible = True

        # Aplica vibrancy nativo na primeira exibição
        if not hasattr(self, '_vibrancy_applied'):
            self._vibrancy_applied = True
            QTimer.singleShot(50, lambda: self._apply_vibrancy(self))

        if duration > 0:
            self.hide_timer.start(duration)

    def update_context_wall(self, data):
        if not data:
            self.context_frame.hide()
            return

        self.file_label.setText(f"FILE  {data.get('file', '--')[:32]}")
        self.linear_label.setText(f"TASK  {data.get('linear', '--')[:32]}")
        self.github_label.setText(f"REPO  {data.get('github', '--')[:32]}")
        
        # Repassa para o VoiceOverlay se ele for o foco visual
        self.voice_overlay.update_context(self.file_label, self.linear_label, self.github_label)
        
        # No HUD normal fica visível apenas se não estivermos em modo voz
        if not self.voice_overlay.isVisible():
            self.context_frame.show()
            self._reposition()
            self.show()

    def _reposition(self):
        screen = self.screen().geometry()
        # Não precisa mais de adjustSize na largura, apenas na altura
        self.setFixedHeight(self.sizeHint().height())
        w = 240
        x = screen.width() - w - 20
        y = 20
        self.move(x, y)

    def _fade_out(self):
        self._visible = False
        self.hide()

    def show_message(self, text, duration=3000):
        self.update_hud(text, "IDLE", duration)
