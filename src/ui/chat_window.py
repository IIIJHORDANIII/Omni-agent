import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, 
                             QPushButton, QHBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from core.llm_client import LLMClient
from core.voice_service import VoiceService
import threading


def _chat_stylesheet():
    return """
        QFrame#MainContainer {
            background-color: rgba(28, 28, 30, 0.92);
            border: 0.5px solid rgba(255, 255, 255, 0.12);
            border-radius: 14px;
        }
    """


class ChatWindow(QWidget):
    append_text_signal = pyqtSignal(str, str)
    update_mic_text_signal = pyqtSignal(str)
    update_input_field_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.voice_service = VoiceService(on_wake_word_detected=None)
        
        # O usuário pediu para não restaurar contexto antigo entre reinicializações do app.
        # Começamos com a memória zerada.
        from core.session_persistence import session_persistence
        self.chat_history = []
        session_persistence.save(messages=self.chat_history)
        
        self.tray_icon = None
        self.is_processing = False
        self.init_ui()
        
        self.append_text_signal.connect(self._safe_append_to_history)
        self.update_mic_text_signal.connect(self._safe_update_mic_text)
        self.update_input_field_signal.connect(self._safe_update_input_field)

    def _rebuild_ui_from_history(self):
        for msg in self.chat_history:
            sender = "Você" if msg["role"] == "user" else "Agente"
            content = msg["content"]
            if msg["role"] == "system":
                continue
            self.text_display.append(f"<b>{sender}:</b> {content}<br>")

    def _safe_update_mic_text(self, text):
        self.mic_btn.setText(text)

    def _safe_update_input_field(self, text):
        self.input_field.setText(text)
        self.send_message()

    def _safe_append_to_history(self, sender, text):
        self.text_display.append(f"<b>{sender}:</b> {text}<br>")
        
        role = "user" if sender in ("Você", "Você (Voz)") else "assistant"
        self.chat_history.append({"role": role, "content": text})
        
        from core.session_persistence import session_persistence
        session_persistence.save(messages=self.chat_history)

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.layout = QVBoxLayout()
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(_chat_stylesheet())
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 16)
        container_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Anders")
        title.setStyleSheet("""
            color: rgba(255, 255, 255, 0.92);
            font-weight: 600;
            font-size: 14px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                color: rgba(255, 255, 255, 0.4);
                border: none;
                font-size: 16px;
                border-radius: 12px;
                background: transparent;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.08); }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        
        container_layout.addLayout(header)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.85);
                font-size: 13px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                selection-background-color: rgba(0, 122, 255, 0.3);
            }
        """)
        container_layout.addWidget(self.text_display)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Digite seu comando...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                border: 0.5px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 10px 14px;
                color: white;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #007aff; }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        self.mic_btn = QPushButton("\U0001f399\ufe0f")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border-radius: 18px;
                color: white;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.12); }
        """)
        self.mic_btn.clicked.connect(self.start_voice_input)
        input_layout.addWidget(self.mic_btn)
        
        container_layout.addLayout(input_layout)
        
        self.layout.addWidget(self.container)
        self.setLayout(self.layout)
        self.resize(400, 500)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text or self.is_processing:
            return
        
        self.input_field.clear()
        self._safe_append_to_history("Você", text)
        
        self.is_processing = True
        
        def _process():
            try:
                response = self.llm_client.chat(self.chat_history)
                self.append_text_signal.emit("Agente", response)
                
                # Evita falar se a resposta for JSON de ferramenta
                is_json_response = response.strip().startswith(("{", "[")) and ("tool" in response or "action" in response or "name" in response)
                
                if response and not is_json_response:
                    self.voice_service.speak(response)
            except Exception as e:
                self.append_text_signal.emit("Erro", f"Falha no processamento: {e}")
            finally:
                self.is_processing = False
        
        threading.Thread(target=_process, daemon=True).start()

    def start_voice_input(self):
        def _listen():
            self.update_mic_text_signal.emit("\U0001f534")
            text = self.voice_service.listen()
            if text:
                self.update_input_field_signal.emit(text)
            self.update_mic_text_signal.emit("\U0001f399\ufe0f")
        
        threading.Thread(target=_listen, daemon=True).start()

    def show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def set_tray_icon(self, tray_icon):
        self.tray_icon = tray_icon

    def process_silent_command(self, text):
        if not text or self.is_processing:
            return
        
        self._safe_append_to_history("Você (Voz)", text)
        self.is_processing = True
        
        def _process():
            try:
                response = self.llm_client.chat(self.chat_history)
                self.append_text_signal.emit("Agente", response)
                
                # Evita falar se a resposta for JSON de ferramenta
                is_json_response = response.strip().startswith(("{", "[")) and ("tool" in response or "action" in response or "name" in response)
                
                if response and not is_json_response:
                    self.voice_service.speak(response)
            except Exception as e:
                self.append_text_signal.emit("Erro", f"Falha no processamento: {e}")
            finally:
                self.is_processing = False
                
        threading.Thread(target=_process, daemon=True).start()
