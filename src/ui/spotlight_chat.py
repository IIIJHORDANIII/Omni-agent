# SpotlightChat implementation: a lightweight overlay mimicking macOS Spotlight
# Provides a QLineEdit for input and a QListWidget for LLM responses.
# The overlay appears on double-Command key press (handled by GlobalHotkeyHandler).


import sys
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPalette, QColor

# Import the LLM client for processing user queries
from core.llm_client import LLMClient


class SpotlightChat(QWidget):
    """Spotlight-style chat overlay.

    The widget is frameless, translucent, and appears on top of all windows.
    It consists of a compact input field and a list of response items that
    appear as pop‑up suggestions. The UI mimics the macOS Spotlight appearance
    without an enclosing box around the entire overlay.
    """

    # Signal emitted when the overlay wants to hide (e.g., after Esc)
    request_hide = pyqtSignal()
    # Signal emitted to safely update the UI from the LLM background thread
    response_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        # Keep a simple history for the current session (optional)
        self.chat_history = []

    def _setup_window(self):
        # Usando Window puro para garantir que pode receber foco do teclado
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        # Initial size – width fixed, height adapts to content
        self.setFixedWidth(500)
        self.move_to_center()

    def move_to_center(self):
        # Position the overlay exactly in the center of the primary screen
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_ui(self):
        # Main container with subtle dark glass effect to match HUD
        self.container = QFrame(self)
        self.container.setObjectName("SpotlightContainer")
        self.container.setStyleSheet(
            """
            QFrame#SpotlightContainer {
                background-color: rgba(0, 0, 0, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
            QLineEdit#InputField {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                color: #ffffff;
                font-size: 15px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
            }
            QLineEdit#InputField::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }
            QLineEdit#InputField:focus {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QListWidget#ResultList {
                background: transparent;
                border: none;
                color: #e0e0e0;
                font-size: 14px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
            }
            QListWidget#ResultList::item {
                padding: 6px 8px;
            }
            QListWidget#ResultList::item:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            """
        )

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Input field – user types the query
        self.input_field = QLineEdit()
        self.input_field.setObjectName("InputField")
        self.input_field.setPlaceholderText("Pergunte ao Anders…")
        layout.addWidget(self.input_field)

        # List widget for showing LLM responses as pop‑up items
        self.result_list = QListWidget()
        self.result_list.setObjectName("ResultList")
        layout.addWidget(self.result_list)

        # Set the container as the central widget
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.container)
        self.setLayout(outer_layout)

    def _connect_signals(self):
        self.input_field.returnPressed.connect(self._on_submit)
        # Escape hides the overlay; also hide when focus is lost for a short period
        self.input_field.installEventFilter(self)
        self.result_list.installEventFilter(self)
        self.request_hide.connect(self.hide)
        self.response_ready.connect(self._display_response)

    def eventFilter(self, source, event):
        # Hide on Esc key
        if event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.hide()
                return True
            # Se o usuário apertar Enter na lista de resultados, volta pro input
            if source == self.result_list and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.show_overlay()
                return True
        return super().eventFilter(source, event)

    def show_overlay(self):
        """Public slot used by GlobalHotkeyHandler to display the overlay."""
        # Força o macOS a dar foco para este app
        if sys.platform == "darwin":
            try:
                from AppKit import NSApp
                NSApp.activateIgnoringOtherApps_(True)
            except ImportError:
                pass
        
        # Clear previous content
        self.input_field.clear()
        self.result_list.clear()
        
        # Estado inicial: Mostra apenas o input, esconde os resultados
        self.input_field.setEnabled(True)
        self.input_field.setReadOnly(False)
        self.input_field.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.input_field.show()
        self.result_list.hide()
        
        # Ajusta a altura de volta para apenas o input field (64px para não espremer o texto)
        self.container.setFixedHeight(64)
        self.setFixedHeight(64)
        self.adjustSize()
        self.move_to_center()
        
        if hasattr(self, 'auto_hide_timer') and self.auto_hide_timer.isActive():
            self.auto_hide_timer.stop()
            
        # Focus the input explicitly
        def _force_focus():
            self.activateWindow()
            self.input_field.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            # Extra garantee for PyQt6 macOS
            if self.windowHandle():
                self.windowHandle().requestActivate()
                
        QTimer.singleShot(100, _force_focus)
        self.show()
        self.raise_()

    def _on_submit(self):
        query = self.input_field.text().strip()
        if not query:
            return
        
        self.input_field.setEnabled(False)
        self.result_list.clear()
        
        # Usuário pediu para sumir enquanto processa
        self.hide()

        # Run LLM call in a background thread to keep UI responsive
        threading.Thread(target=self._process_query, args=(query,), daemon=True).start()

    def _process_query(self, query: str):
        try:
            # Simple one‑shot chat – we keep a minimal history for context
            messages = self.chat_history + [{"role": "user", "content": query}]
            response = self.llm_client.chat(messages)
            # Append to history for potential follow‑up within the same overlay session
            self.chat_history.append({"role": "user", "content": query})
            self.chat_history.append({"role": "assistant", "content": response})
            # Update UI on the main thread via signal
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"Erro: {e}")
        finally:
            # Cannot call UI methods directly, rely on the signal handler or a generic reset method if needed
            # But the response_ready will show the result list anyway.
            pass

    def _display_response(self, text: str):
        self.result_list.clear()
        # Split long responses into separate list items for better readability
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                item = QListWidgetItem(line)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.result_list.addItem(item)
                
        # Auto‑resize height based on content (max 6 items visible)
        visible_count = max(1, min(self.result_list.count(), 6))
        item_height = self.result_list.sizeHintForRow(0)
        if item_height < 10: item_height = 24
        new_height = visible_count * item_height + 16
        self.result_list.setFixedHeight(new_height)
        
        # Mostra o overlay novamente, mas SÓ com a resposta
        self.input_field.hide()
        self.result_list.show()
        
        # Ajusta a altura da janela principal para abraçar os itens
        self.container.setFixedHeight(new_height + 24)
        self.setFixedHeight(new_height + 24)
        
        self.adjustSize()
        self.move_to_center()
        self.show()
        self.raise_()
        self.activateWindow()
        self.result_list.setFocus()
        
        # Timer para sumir automaticamente após 8 segundos
        if not hasattr(self, 'auto_hide_timer'):
            self.auto_hide_timer = QTimer(self)
            self.auto_hide_timer.setSingleShot(True)
            self.auto_hide_timer.timeout.connect(self.hide)
        
        # Reinicia o timer para 8 segundos (8000ms)
        self.auto_hide_timer.start(8000)

    # Optional: expose a method to programmatically close the overlay
    def close_overlay(self):
        self.hide()

# End of SpotlightChat implementation
