import sys
import os
import threading
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QHBoxLayout, QFrame, QStackedWidget,
                             QProgressBar, QApplication, QDialog, QComboBox,
                             QCheckBox, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


def _apple_btn_style(accent=False):
    if accent:
        return """
            QPushButton {
                background-color: #007aff;
                color: white;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 24px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #0066d6; }
            QPushButton:pressed { background-color: #004ea2; }
            QPushButton:disabled { background-color: rgba(0, 122, 255, 0.4); }
        """
    return """
        QPushButton {
            background-color: rgba(255, 255, 255, 0.08);
            color: rgba(255, 255, 255, 0.85);
            font-weight: 500;
            border-radius: 8px;
            padding: 10px 24px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
            font-size: 13px;
            border: 0.5px solid rgba(255, 255, 255, 0.1);
        }
        QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); }
    """


class StyledPage(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(12)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("""
            color: rgba(255, 255, 255, 0.92);
            font-size: 20px;
            font-weight: 700;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("""
            color: rgba(255, 255, 255, 0.5);
            font-size: 13px;
            font-weight: 400;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        lbl_sub.setWordWrap(True)
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_sub)

    def add_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 11px;
            font-weight: 600;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        self.layout.addWidget(lbl)
        return lbl


class WelcomePage(StyledPage):
    def __init__(self, parent=None):
        super().__init__("Anders Setup", "Configure seu assistente pessoal.", parent)
        self.add_label("Seu Nome")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Como devo chamá-lo?")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.06);
                border: 0.5px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px 12px;
                color: white;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #007aff;
            }
        """)
        self.layout.addWidget(self.name_input)

        self.add_label("Personalidade")
        self.personality = QComboBox()
        self.personality.addItems(["Anders (Formal / Leal)", "H.A.L (Frio / Eficiente)", "Samantha (Amigável / Proativo)"])
        self.personality.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.06);
                color: white;
                border: 0.5px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px 12px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 13px;
            }
            QComboBox:focus { border-color: #007aff; }
            QComboBox QAbstractItemView {
                background-color: #1c1c1e;
                color: white;
                border: 0.5px solid rgba(255, 255, 255, 0.1);
                selection-background-color: #007aff;
                selection-color: white;
            }
        """)
        self.layout.addWidget(self.personality)
        self.layout.addStretch()


class VoicePage(StyledPage):
    SAMPLES = [
        ("wake_1", "Diga: Anders"),
        ("wake_2", "Diga: Anders (mais natural, como falaria de dia)"),
        ("wake_phrase_1", "Diga: Anders, qual o clima?"),
        ("wake_phrase_2", "Diga: Anders, me mostra os e-mails de hoje"),
        ("full_word", "Diga: Anders Agent"),
        ("command_1", "Diga: Anders, abre o VS Code"),
        ("command_2", "Diga: Anders, cria um commit com a mensagem de deploy"),
        ("conversation", "Diga: Anders, como está a bateria?"),
        ("whisper", "Diga: Anders (sussurrando)"),
        ("natural", "Diga qualquer frase que comece com Anders"),
    ]

    def __init__(self, parent=None):
        super().__init__("Assinatura de Voz", "Registre sua voz para que só você possa ativá-lo.\nQuanto mais amostras, mais precisa a verificação.", parent)

        self._audio_samples = []
        self._current_sample = 0
        self._recording = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }
        """)

        v_frame = QFrame()
        v_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.04);
                border: 0.5px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        v_layout = QVBoxLayout(v_frame)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(8)

        self.step_label = QLabel("PASSO 1 DE 10")
        self.step_label.setStyleSheet("""
            color: #007aff;
            font-size: 11px;
            font-weight: 600;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        v_layout.addWidget(self.step_label)

        self.prompt_label = QLabel(self.SAMPLES[0][1])
        self.prompt_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.85);
            font-size: 14px;
            font-weight: 600;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self.prompt_label)

        self.voice_status = QLabel("Pressione para gravar")
        self.voice_status.setStyleSheet("""
            color: rgba(255, 255, 255, 0.4);
            font-size: 11px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        v_layout.addWidget(self.voice_status)

        self.record_btn = QPushButton("Gravar")
        self.record_btn.setStyleSheet(_apple_btn_style(accent=True))
        self.record_btn.setFixedWidth(200)
        self.record_btn.clicked.connect(self._toggle_record)
        v_layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dots_layout = QHBoxLayout()
        dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dots = []
        for i in range(10):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet("background: rgba(255,255,255,0.15); border-radius: 4px;")
            dots_layout.addWidget(dot)
            self.dots.append(dot)
        v_layout.addLayout(dots_layout)

        self.embedding_status = QLabel("")
        self.embedding_status.setStyleSheet("""
            color: rgba(255, 255, 255, 0.5);
            font-size: 10px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        self.embedding_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self.embedding_status)

        scroll.setWidget(v_frame)
        self.layout.addWidget(scroll)
        self.layout.addStretch()

    def _toggle_record(self):
        if self._recording:
            return
        self._start_recording()

    def _start_recording(self):
        self._recording = True
        self.record_btn.setEnabled(False)
        duration = 4 if self._current_sample >= 5 else 3
        self.voice_status.setText(f"Gravando... ({duration}s)")
        self.voice_status.setStyleSheet("color: #ff453a; font-weight: 500;")
        self.dots[self._current_sample].setStyleSheet("background: #ff453a; border-radius: 4px;")

        def _rec():
            import pyaudio
            import numpy as _np
            try:
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
                frames = []
                for _ in range(0, int(16000 / 1024 * duration)):
                    frames.append(stream.read(1024))
                stream.stop_stream()
                stream.close()
                p.terminate()

                audio_np = _np.frombuffer(b''.join(frames), dtype=_np.int16).astype(_np.float32) / 32768.0
                self._audio_samples.append(audio_np)

                import wave
                memory_db_dir = os.path.expanduser("~/Documents/pessoal/agent/memory_db")
                os.makedirs(memory_db_dir, exist_ok=True)
                filename = os.path.join(memory_db_dir, f"voice_sample_{self._current_sample + 1}.wav")
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(frames))

                QTimer.singleShot(0, self._on_sample_done)
            except Exception as e:
                print(f"Erro na gravação: {e}")
                QTimer.singleShot(0, self._on_sample_error)

        threading.Thread(target=_rec, daemon=True).start()

    def _on_sample_done(self):
        self.dots[self._current_sample].setStyleSheet("background: #34c759; border-radius: 4px;")
        self._current_sample += 1

        if self._current_sample < len(self.SAMPLES):
            self.step_label.setText(f"PASSO {self._current_sample + 1} DE 10")
            self.prompt_label.setText(self.SAMPLES[self._current_sample][1])
            self.voice_status.setText("Pressione para gravar")
            self.voice_status.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11px;")
            self.record_btn.setEnabled(True)
            self._recording = False
        else:
            self.voice_status.setText("Processando perfil de voz...")
            self.voice_status.setStyleSheet("color: #007aff; font-weight: 500;")
            self.step_label.setText("PERFIL DE VOZ")
            self.prompt_label.setText("Criando assinatura biométrica...")
            self.record_btn.hide()
            threading.Thread(target=self._generate_embedding, daemon=True).start()

    def _on_sample_error(self):
        self.voice_status.setText("Erro na gravação. Tente novamente.")
        self.voice_status.setStyleSheet("color: #ff453a; font-weight: 500;")
        self.record_btn.setEnabled(True)
        self._recording = False

    def _generate_embedding(self):
        try:
            from core.speaker_verification import speaker_verifier

            success = speaker_verifier.enroll_from_samples(self._audio_samples)

            if success:
                QTimer.singleShot(0, lambda: self.voice_status.setText("Perfil de voz criado com sucesso!"))
                QTimer.singleShot(0, lambda: self.voice_status.setStyleSheet("color: #34c759; font-weight: 600;"))
                QTimer.singleShot(0, lambda: self.embedding_status.setText(f"Perfil registrado com {len(self._audio_samples)} amostras. Agora só você pode ativá-lo."))
                QTimer.singleShot(0, lambda: self.embedding_status.setStyleSheet("color: #34c759; font-size: 11px;"))
                QTimer.singleShot(0, lambda: self.prompt_label.setText("Perfil registrado!"))
            else:
                QTimer.singleShot(0, lambda: self.voice_status.setText("Erro ao criar perfil. Tente novamente."))
                QTimer.singleShot(0, lambda: self.voice_status.setStyleSheet("color: #ff453a; font-weight: 500;"))
        except Exception as e:
            print(f"Erro ao gerar embedding: {e}")
            QTimer.singleShot(0, lambda: self.voice_status.setText(f"Erro: {e}"))
            QTimer.singleShot(0, lambda: self.voice_status.setStyleSheet("color: #ff453a; font-weight: 500;"))


class ConnectPage(StyledPage):
    def __init__(self, parent=None):
        super().__init__("Conexões", "Configure suas chaves de API. Deixe vazio para rodar 100% local.", parent)
        self.inputs = {}
        
        # Container com Scroll para as chaves
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
        """)
        
        scroll_content = QFrame()
        scroll_content.setStyleSheet("background: transparent; border: none;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(10)

        keys = [
            ("DEEPSEEK_API_KEY", "DeepSeek API (Recomendado)"),
            ("ANTHROPIC_API_KEY", "Anthropic Claude"),
            ("GOOGLE_GENERATIVE_AI_API_KEY", "Google Gemini"),
            ("GITHUB_TOKEN", "GitHub Token (Para ler PRs/Issues)"),
            ("LINEAR_API_KEY", "Linear API Key (Para tarefas)"),
        ]
        
        for env, label in keys:
            lbl = QLabel(label)
            lbl.setStyleSheet("""
                color: rgba(255, 255, 255, 0.6);
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            """)
            scroll_layout.addWidget(lbl)
            
            edit = QLineEdit()
            edit.setPlaceholderText("sk-..." if "DEEPSEEK" in env else "Cole sua chave aqui")
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setStyleSheet("""
                QLineEdit {
                    background: rgba(255, 255, 255, 0.06);
                    border: 0.5px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: white;
                    font-family: 'Menlo', monospace;
                    font-size: 12px;
                }
                QLineEdit:focus { border-color: #007aff; }
            """)
            scroll_layout.addWidget(edit)
            self.inputs[env] = edit

        self.vision_check = QCheckBox("Habilitar Visão (Qwen2-VL)")
        self.vision_check.setChecked(True)
        self.vision_check.setStyleSheet("""
            QCheckBox {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                spacing: 8px;
                margin-top: 10px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QCheckBox::indicator:checked {
                background: #007aff;
                border-color: #007aff;
            }
        """)
        scroll_layout.addWidget(self.vision_check)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        self.layout.addWidget(scroll)

        self.mode_label = QLabel("")
        self.mode_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px;")
        self.mode_label.setWordWrap(True)
        self.layout.addWidget(self.mode_label)

        for edit in self.inputs.values():
            edit.textChanged.connect(self._update_mode_label)
        self._update_mode_label()

    def _update_mode_label(self):
        has_deepseek = bool(self.inputs.get("DEEPSEEK_API_KEY", QLineEdit()).text().strip())
        has_anthropic = bool(self.inputs.get("ANTHROPIC_API_KEY", QLineEdit()).text().strip())
        has_google = bool(self.inputs.get("GOOGLE_GENERATIVE_AI_API_KEY", QLineEdit()).text().strip())

        if has_deepseek:
            self.mode_label.setText("Modo: Cloud (DeepSeek) — sem modelos locais em RAM")
            self.mode_label.setStyleSheet("color: #34c759; font-size: 11px; font-family: '.AppleSystemUIFont', -apple-system, sans-serif;")
        elif has_anthropic:
            self.mode_label.setText("Modo: Cloud (Anthropic Claude) — sem modelos locais em RAM")
            self.mode_label.setStyleSheet("color: #34c759; font-size: 11px; font-family: '.AppleSystemUIFont', -apple-system, sans-serif;")
        elif has_google:
            self.mode_label.setText("Modo: Cloud (Google Gemini) — sem modelos locais em RAM")
            self.mode_label.setStyleSheet("color: #34c759; font-size: 11px; font-family: '.AppleSystemUIFont', -apple-system, sans-serif;")
        else:
            self.mode_label.setText("Modo: Local (DeepSeek-R1 1.5B via MLX) — requer ~2GB de RAM")
            self.mode_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; font-family: '.AppleSystemUIFont', -apple-system, sans-serif;")


class SetupWizard(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anders Setup")
        self.setFixedSize(480, 620)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("MainFrame")
        self.container.setStyleSheet("""
            #MainFrame {
                background-color: rgba(28, 28, 30, 0.97);
                border: 0.5px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)

        cont_layout = QVBoxLayout(self.container)
        cont_layout.setContentsMargins(0, 0, 0, 16)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.setStyleSheet("""
            QProgressBar { background: rgba(255, 255, 255, 0.06); border: none; }
            QProgressBar::chunk { background-color: #007aff; border-radius: 1px; }
        """)
        self.progress.setTextVisible(False)
        cont_layout.addWidget(self.progress)

        header = QHBoxLayout()
        header.addStretch()
        close = QPushButton("×")
        close.setFixedSize(28, 28)
        close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.4);
                font-size: 18px;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.08); }
        """)
        close.clicked.connect(self.reject)
        header.addWidget(close)
        header.setContentsMargins(0, 8, 12, 0)
        cont_layout.addLayout(header)

        self.stack = QStackedWidget()
        self.p1 = WelcomePage()
        self.p2 = VoicePage()
        self.p3 = ConnectPage()
        for p in [self.p1, self.p2, self.p3]:
            self.stack.addWidget(p)
        cont_layout.addWidget(self.stack)

        nav = QHBoxLayout()
        nav.setContentsMargins(32, 0, 32, 16)
        self.btn_back = QPushButton("Voltar")
        self.btn_back.setStyleSheet(_apple_btn_style())
        self.btn_next = QPushButton("Próximo")
        self.btn_next.setStyleSheet(_apple_btn_style(accent=True))
        self.btn_back.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        nav.addWidget(self.btn_back)
        nav.addSpacing(12)
        nav.addWidget(self.btn_next)
        cont_layout.addLayout(nav)

        self.main_layout.addWidget(self.container)
        self._drag_pos = None
        self.update_ui()

    def update_ui(self):
        idx = self.stack.currentIndex()
        total = 3
        self.progress.setValue(int(((idx + 1) / total) * 100))
        self.btn_back.setVisible(idx > 0)
        if idx == total - 1:
            self.btn_next.setText("Ativar Sistema")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #34c759;
                    color: white;
                    font-weight: 600;
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                    font-size: 13px;
                    border: none;
                }
                QPushButton:hover { background-color: #2db84e; }
            """)
        else:
            self.btn_next.setText("Próximo")
            self.btn_next.setStyleSheet(_apple_btn_style(accent=True))

    def next_page(self):
        if self.stack.currentIndex() < 2:
            self.stack.setCurrentIndex(self.stack.currentIndex() + 1)
            self.update_ui()
        else:
            self.finish()

    def prev_page(self):
        self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self.update_ui()

    def finish(self):
        print("SetupWizard: Finalizando...")
        env_lines = [f"USER_NAME={self.p1.name_input.text() or 'Mestre'}"]
        for k, v in self.p3.inputs.items():
            val = v.text().strip()
            if val:
                env_lines.append(f"{k}={val}")

        vision_enabled = "true" if self.p3.vision_check.isChecked() else "false"
        env_lines.append(f"VISION_ENABLED={vision_enabled}")

        personality = self.p1.personality.currentText()
        env_lines.append(f"PERSONALITY={personality}")

        # Caminho absoluto para garantir persistência no macOS Bundle
        env_path = os.path.expanduser("~/Documents/pessoal/agent/.env")
        os.makedirs(os.path.dirname(env_path), exist_ok=True)

        with open(env_path, "w") as f:
            f.write("\n".join(env_lines))

        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)

        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    SetupWizard().show()
    sys.exit(app.exec())