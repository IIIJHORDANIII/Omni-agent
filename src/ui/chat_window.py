import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, 
                             QPushButton, QHBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG
from core.llm_client import LLMClient
from core.voice_service import VoiceService
import threading

class ChatWindow(QWidget):
    # Sinal para atualizar a UI a partir de threads de background
    append_text_signal = pyqtSignal(str, str)
    update_mic_text_signal = pyqtSignal(str)
    update_input_field_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        # Passa None explicitamente para evitar erros de assinatura se o motor estiver dessincronizado
        self.voice_service = VoiceService(on_wake_word_detected=None)
        
        # Carrega estado persistente (Fase 5 - Production Ready)
        from core.session_persistence import session_persistence
        saved_state = session_persistence.load()
        self.chat_history = saved_state.get("messages", [])
        
        self.tray_icon = None
        self.is_processing = False
        self.init_ui()
        
        # Reconstrói se houver histórico
        if self.chat_history:
            self._rebuild_ui_from_history()
        
        # Conecta os sinais
        self.append_text_signal.connect(self._safe_append_to_history)
        self.update_mic_text_signal.connect(self._safe_update_mic_text)
        self.update_input_field_signal.connect(self._safe_update_input_field)

    def _rebuild_ui_from_history(self):
        for msg in self.chat_history:
            sender = "VOCÊ" if msg["role"] == "user" else "AGENTE"
            content = msg["content"]
            # Pula mensagens de sistema no display
            if msg["role"] == "system": continue
            self.text_display.append(f"<b>{sender}:</b> {content}<br>")

    def _safe_update_mic_text(self, text):
        self.mic_btn.setText(text)

    def _safe_update_input_field(self, text):
        self.input_field.setText(text)
        self.send_message()

    def _safe_append_to_history(self, sender, text):
        self.text_display.append(f"<b>{sender}:</b> {text}<br>")
        
        # Atualiza o histórico para o LLM e persiste
        role = "user" if sender == "VOCÊ" else "assistant"
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
        
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(35, 35)
        self.mic_btn.setStyleSheet("background: rgba(255, 255, 255, 15); border-radius: 17px; color: white;")
        self.mic_btn.clicked.connect(self.start_voice_input)
        input_layout.addWidget(self.mic_btn)
        
        container_layout.addLayout(input_layout)
        
        self.layout.addWidget(self.container)
        self.setLayout(self.layout)
        self.resize(400, 500)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text or self.is_processing: return
        
        self.input_field.clear()
        self._safe_append_to_history("VOCÊ", text)
        
        self.is_processing = True
        
        def _process():
            try:
                # O chat do LLMClient já retorna a resposta e executa ferramentas via ToolDispatcher
                response = self.llm_client.chat(self.chat_history)
                self.append_text_signal.emit("AGENTE", response)
                
                # Se houver resposta de voz, fala
                if response and not response.startswith("[{"):
                    self.voice_service.speak(response)
            except Exception as e:
                self.append_text_signal.emit("ERRO", f"Falha no processamento: {e}")
            finally:
                self.is_processing = False
        
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
        if not text or self.is_processing: return
        
        self._safe_append_to_history("VOCÊ (Voz)", text)
        self.is_processing = True
        
        def _process():
            try:
                response = self.llm_client.chat(self.chat_history)
                self.append_text_signal.emit("AGENTE", response)
                
                # Responde por voz obrigatoriamente já que o input foi por voz
                if response and not response.startswith("[{"):
                    self.voice_service.speak(response)
            except Exception as e:
                self.append_text_signal.emit("ERRO", f"Falha no processamento: {e}")
            finally:
                self.is_processing = False
                
        threading.Thread(target=_process, daemon=True).start()
