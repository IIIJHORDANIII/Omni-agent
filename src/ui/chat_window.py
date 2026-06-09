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
        self.chat_history = []
        self.tray_icon = None
        self.init_ui()
        
        # Conecta os sinais
        self.append_text_signal.connect(self._safe_append_to_history)
        self.update_mic_text_signal.connect(self._safe_update_mic_text)
        self.update_input_field_signal.connect(self._safe_update_input_field)

    def _safe_update_mic_text(self, text):
        self.mic_btn.setText(text)

    def _safe_update_input_field(self, text):
        self.input_field.setText(text)
        self.send_message()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
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
        self.setFixedSize(400, 500)

    def set_tray_icon(self, tray_icon):
        self.tray_icon = tray_icon

    def show_and_activate(self):
        if self.tray_icon:
            geom = self.tray_icon.geometry()
            self.move(geom.x() - self.width() + geom.width(), geom.y() + geom.height() + 5)
        
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def append_to_history(self, text, role):
        # Emite sinal para garantir que a UI seja atualizada na Main Thread
        self.append_text_signal.emit(text, role)

    def _safe_append_to_history(self, text, role):
        self.chat_history.append({"role": role, "content": text})
        color = "#888888" if role == "system" else ("#4a9eff" if role == "user" else "#a0a0a0")
        prefix = "Sistema" if role == "system" else ("Você" if role == "user" else "Agente")
        self.text_display.append(f'<b style="color: {color};">{prefix}:</b> {text}<br>')
        # Scroll para o fim
        self.text_display.verticalScrollBar().setValue(self.text_display.verticalScrollBar().maximum())

    def send_message(self):
        text = self.input_field.text().strip()
        if not text: return
        
        self.input_field.clear()
        self.append_to_history(text, "user")
        
        threading.Thread(target=self._process_response, args=(text,), daemon=True).start()

    def _process_response(self, text):
        # O MLX pode ser lento, então rodamos em background
        
        # Verifica se o usuário pediu análise da tela
        vision_keywords = ["resumo da tela", "o que tem na tela", "analise a tela", "descreva a tela", "oq tem na tela", "vê a tela"]
        if any(keyword in text.lower() for keyword in vision_keywords):
            self.append_to_history("Capturando e analisando tela...", "system")
            try:
                image_b64 = self.llm_client.vision_service.capture_screen_base64()
                if image_b64:
                    prompt = f"O usuário pediu: '{text}'. Descreva o que está na tela baseado nesse pedido."
                    response = self.llm_client.chat(
                        messages=[{"role": "user", "content": prompt}],
                        include_vision=True,
                        image_b64=image_b64
                    )
                    if response:
                        self.append_to_history(response, "assistant")
                        self.voice_service.speak(response)
                        return
            except Exception as e:
                self.append_to_history(f"Erro na análise: {e}", "system")

        # Comportamento padrão de chat
        response = self.llm_client.chat(self.chat_history)
        if response:
            self.append_to_history(response, "assistant")
            self.voice_service.speak(response)

    def process_silent_command(self, text):
        """Processa comando vindo da Wake Word."""
        self.append_to_history(text, "user")
        threading.Thread(target=self._process_response, args=(text,), daemon=True).start()

    def start_voice_input(self):
        self.update_mic_text_signal.emit("🔴")
        def _listen():
            text = self.voice_service.listen()
            if text:
                self.update_input_field_signal.emit(text)
            
            self.update_mic_text_signal.emit("🎤")
        
        threading.Thread(target=_listen, daemon=True).start()
