from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPainterPath, QPen, QLinearGradient
import math
import random

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


class AudioSpectrumWidget(QWidget):
    """Vertical Bar Spectrum Equalizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_bars = 40 # Dobro de barras para ser mais fino e detalhado
        self.bars = [0.0] * self.num_bars
        self.targets = [0.0] * self.num_bars
        self._mode = "idle"
        self._color = QColor(255, 255, 255, 180)
        
        self.setFixedSize(160, 40) # Widget menor
        
        # Timer para suavização interna
        self.smooth_timer = QTimer()
        self.smooth_timer.timeout.connect(self._smooth_bars)
        self.smooth_timer.start(16) # ~60fps

    def set_spectrum(self, data):
        """Recebe array de float."""
        if not data: return
        # Como temos 40 barras mas a FFT retorna 20 bins, vamos interpolar ou duplicar
        for i in range(self.num_bars):
            source_idx = i // 2 # Mapeia 40 barras para 20 bins
            if source_idx < len(data):
                val = data[source_idx]
            else:
                val = 0.0
            
            # Rearranjo para centralizar (montanha)
            # Logica de espelhamento para 40 barras
            if i < 20:
                # Lado esquerdo (altas -> baixas)
                idx = 19 - i
            else:
                # Lado direito (baixas -> altas)
                idx = i - 20
            
            # Sensibilidade em 0.3 conforme solicitado anteriormente
            self.targets[i] = max(0.05, min(1.0, data[idx] * 0.3)) if idx < len(data) else 0.05

    def set_mode(self, state: str):
        self._mode = state.lower()
        if self._mode == "listening":
            self._color = QColor(255, 255, 255, 220)
        elif self._mode == "speaking":
            self._color = QColor(255, 59, 48, 220)
        elif self._mode in ["thinking", "processing"]:
            self._color = QColor(255, 214, 10, 220)
        else:
            self._color = QColor(255, 255, 255, 100)

    def _smooth_bars(self):
        # Queda suave (decay)
        for i in range(self.num_bars):
            if self.targets[i] > self.bars[i]:
                self.bars[i] += (self.targets[i] - self.bars[i]) * 0.4
            else:
                self.bars[i] -= (self.bars[i] - self.targets[i]) * 0.15
            
            if self._mode != "idle":
                 self.targets[i] *= 0.92
            else:
                 self.targets[i] = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        bar_w = (w / self.num_bars) - 1 # Barras bem finas
        
        for i in range(self.num_bars):
            bar_h = max(2, self.bars[i] * h) 
            x = i * (bar_w + 1)
            y = (h - bar_h) / 2
            
            rect = QRectF(x, y, bar_w, bar_h)
            
            grad = QLinearGradient(x, y, x, y + bar_h)
            c1 = QColor(self._color)
            c2 = QColor(self._color)
            c2.setAlpha(int(c2.alpha() * 0.4))
            grad.setColorAt(0, c1)
            grad.setColorAt(1, c2)
            
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            # Arredondamento menor para barras finas
            p.drawRoundedRect(rect, bar_w/2, bar_w/2)
            
        p.end()


class VoiceOverlay(QWidget):
    """HUD Clássico: Retângulo com Blur + Espectro Reativo (Compacto)."""

    def __init__(self):
        super().__init__()
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

        # LARGURA REDUZIDA: 180px
        self.setFixedWidth(180)
        self._position()

    def _position(self):
        screen = self.screen().geometry()
        self.move(screen.width() - self.width() - 20, 20)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("OverlayBG")
        self.bg_frame.setStyleSheet("""
            #OverlayBG {
                background-color: rgba(10, 10, 12, 0.75);
                border: 0.5px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(10, 8, 10, 8)
        bg_layout.setSpacing(6)

        # 1. Espectro (Compacto)
        self.spectrum = AudioSpectrumWidget()
        bg_layout.addWidget(self.spectrum, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 2. Tags (Contexto)
        self.tags_container = QFrame()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(4, 2, 4, 2)
        self.tags_layout.setSpacing(2)
        bg_layout.addWidget(self.tags_container)
        
        self.main_layout.addWidget(self.bg_frame)
        self.bg_frame.hide()

    def set_state(self, state: str):
        self.spectrum.set_mode(state)
        
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
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 9px; font-family: 'Menlo'; background: transparent;")
            lbl.setFixedWidth(210)
            self.tags_layout.addWidget(lbl)
        
        self.bg_frame.show()
        self.show()

    def set_spectrum(self, data):
        self.spectrum.set_spectrum(data)

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
