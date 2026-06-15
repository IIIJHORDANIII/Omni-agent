import sys
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QHBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
import threading


def markdown_to_html(text):
    """Converte Markdown basico para HTML para exibicao no QTextEdit."""
    if not text:
        return text

    # Code blocks (```lang ... ```)
    def replace_code_block(m):
        lang = m.group(1) or ""
        code = m.group(2)
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<pre style="background-color:#1a1a2e; color:#e0e0e0; padding:8px; border-radius:6px; font-family:monospace; font-size:11px;">{code}</pre>'

    text = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, text, flags=re.DOTALL)

    # Inline code (`code`)
    text = re.sub(r'`([^`]+)`', r'<code style="background-color:#1a1a2e; color:#00d4ff; padding:2px 4px; border-radius:3px; font-family:monospace;">\1</code>', text)

    # Bold (**text**)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Italic (*text*)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

    # Headers (### -> ### style)
    text = re.sub(r'^### (.+)$', r'<h4 style="color:#af52de; margin:4px 0;">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h3 style="color:#af52de; margin:4px 0;">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h2 style="color:#af52de; margin:4px 0;">\1</h2>', text, flags=re.MULTILINE)

    # Lists (- item)
    text = re.sub(r'^- (.+)$', r'  \1', text, flags=re.MULTILINE)

    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a style="color:#00d4ff;">\1</a>', text)

    # Newlines
    text = text.replace('\n', '<br>')

    return text

class ChatWindow(QWidget):
    append_text_signal = pyqtSignal(str, str)
    update_mic_text_signal = pyqtSignal(str)
    update_input_field_signal = pyqtSignal(str)
    loading_done_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._llm_client = None
        self._voice_service = None
        
        from core.session_persistence import session_persistence
        saved_state = session_persistence.load()
        self.chat_history = saved_state.get("messages", [])
        self._history_lock = threading.Lock()
        
        self.tray_icon = None
        self.is_processing = False
        self.init_ui()
        
        if self.chat_history:
            self._rebuild_ui_from_history()
        
        self.append_text_signal.connect(self._safe_append_to_history)
        self.update_mic_text_signal.connect(self._safe_update_mic_text)
        self.update_input_field_signal.connect(self._safe_update_input_field)
        self.loading_done_signal.connect(self._on_loading_done)

    @property
    def llm_client(self):
        if self._llm_client is None:
            from core.llm_client import LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    @property
    def voice_service(self):
        if self._voice_service is None:
            from core.voice_service import VoiceService
            self._voice_service = VoiceService(on_wake_word_detected=None)
        return self._voice_service

    def _rebuild_ui_from_history(self):
        for msg in self.chat_history:
            sender = "VOCE" if msg["role"] == "user" else "AGENTE"
            content = msg["content"]
            if msg["role"] == "system": continue
            html_content = markdown_to_html(content)
            self.text_display.append(f"<b>{sender}:</b> {html_content}")

    def _safe_update_mic_text(self, text):
        self.mic_btn.setText(text)

    def _safe_update_input_field(self, text):
        self.input_field.setText(text)
        self.send_message()

    def _on_loading_done(self):
        """Chamado na thread principal quando o processamento termina."""
        self.loading_label.hide()
        self.input_field.setEnabled(True)

    def _safe_append_to_history(self, sender, text):
        html_text = markdown_to_html(text)
        self.text_display.append(f"<b>{sender}:</b> {html_text}")
        
        role = "user" if "VOCE" in sender or "VOCÊ" in sender else "assistant"
        with self._history_lock:
            self.chat_history.append({"role": role, "content": text})
        
        from core.session_persistence import session_persistence
        session_persistence.save(messages=self.chat_history)

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.main_layout = QVBoxLayout()
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            #MainContainer {
                background-color: rgba(30, 30, 30, 230);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Omniscient Agent")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("color: gray; border: none; font-size: 18px;")
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        
        container_layout.addLayout(header)
        
        # Chat display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("background: transparent; border: none; color: #e0e0e0; font-size: 13px;")
        container_layout.addWidget(self.text_display)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Digite seu comando...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 20);
                border-radius: 10px;
                padding: 8px;
                color: white;
                border: 1px solid rgba(255, 255, 255, 10);
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.mic_btn = QPushButton("\U0001f3a4")
        self.mic_btn.setFixedSize(35, 35)
        self.mic_btn.setStyleSheet("background: rgba(255, 255, 255, 15); border-radius: 17px; color: white;")
        self.mic_btn.clicked.connect(self.start_voice_input)
        input_layout.addWidget(self.mic_btn)

        container_layout.addLayout(input_layout)

        # Loading indicator (hidden by default)
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #af52de; font-size: 11px; padding: 2px 8px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.hide()
        container_layout.addWidget(self.loading_label)
        
        self.main_layout.addWidget(self.container)
        self.setLayout(self.main_layout)
        self.resize(400, 500)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text or self.is_processing: return
        
        self.input_field.clear()
        self._safe_append_to_history("VOCE", text)
        
        self.is_processing = True
        self.loading_label.setText("Processando...")
        self.loading_label.show()
        self.input_field.setEnabled(False)
        
        def _process():
            try:
                response = self.llm_client.chat(self.chat_history)
                self.append_text_signal.emit("AGENTE", response)
                
                if response and not response.startswith("[{"):
                    self.voice_service.speak(response)
            except Exception as e:
                self.append_text_signal.emit("ERRO", f"Falha no processamento: {e}")
            finally:
                self.is_processing = False
                self.loading_done_signal.emit()
        
        threading.Thread(target=_process, daemon=True).start()

    def start_voice_input(self):
        def _listen():
            self.update_mic_text_signal.emit("🔴")
            text = self.voice_service.listen()
            if text:
                self.update_input_field_signal.emit(text)
            
            self.update_mic_text_signal.emit("🎤")
        
        threading.Thread(target=_listen, daemon=True).start()

    def show_and_activate(self):
        """Exibe a janela do chat, traz para frente e foca o campo de input."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def set_tray_icon(self, tray_icon):
        """Associa o ícone da bandeja para notificações."""
        self.tray_icon = tray_icon

    def process_silent_command(self, text):
        """Processa um comando de voz recebido em background (sem digitar no campo)."""
        if not text or self.is_processing:
            print(f"DEBUG VOZ: Comando ignorado (text={bool(text)}, processing={self.is_processing})")
            return
        
        self._safe_append_to_history("VOCÊ (Voz)", text)
        self.is_processing = True
        
        def _process():
            try:
                print(f"DEBUG VOZ: Chamando LLM com {len(self.chat_history)} mensagens...")
                response = self.llm_client.chat(self.chat_history)
                print(f"DEBUG VOZ: Resposta do LLM: '{response[:100] if response else 'VAZIA'}'")
                self.append_text_signal.emit("AGENTE", response)
                
                if response and not response.startswith("[{"):
                    self.voice_service.speak(response)
                else:
                    print(f"DEBUG VOZ: Resposta nao falada (starts with [{{ ou vazia)")
            except Exception as e:
                print(f"DEBUG VOZ: ERRO: {e}")
                self.append_text_signal.emit("ERRO", f"Falha no processamento: {e}")
            finally:
                self.is_processing = False
                
        threading.Thread(target=_process, daemon=True).start()
