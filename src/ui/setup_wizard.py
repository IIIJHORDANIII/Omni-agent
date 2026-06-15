import sys
import os
import json
import time
import threading
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QHBoxLayout, QFrame, QStackedWidget,
                             QProgressBar, QApplication, QDialog, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize, QObject, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QColor, QImage, QPixmap

# --- WORKER DE CÂMERA ---
class CameraWorker(QObject):
    """Worker para capturar frames da webcam e emitir sinais Qt."""
    new_frame = pyqtSignal(QImage)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None

    def start_capture(self):
        if self.running: return
        print("CameraWorker: Iniciando captura...")
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            import cv2
            self.cap = cv2.VideoCapture(0)
            if not self.cap or not self.cap.isOpened():
                print("CameraWorker: Câmera não encontrada.")
                self.error.emit("Câmera não detectada.")
                return
                
            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    qt_img = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
                    self.new_frame.emit(qt_img.copy())
                time.sleep(0.03)
                
            if self.cap:
                self.cap.release()
                self.cap = None
        except Exception as e:
            print(f"CameraWorker Erro: {e}")
            self.error.emit(str(e))

    def stop(self):
        self.running = False

    def get_snapshot(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret: return frame
        return None

# --- CLASSES BASE ---
class StyledPage(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 20, 40, 20)
        self.layout.setSpacing(15)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #00d4ff; font-size: 22px; font-weight: 900; letter-spacing: 2px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_title)
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #aaaaaa; font-size: 13px; font-weight: 500;")
        lbl_sub.setWordWrap(True)
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_sub)

    def add_label(self, text):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet("color: #00d4ff; font-size: 11px; font-weight: 800; margin-top: 10px;")
        self.layout.addWidget(lbl)
        return lbl

# --- PÁGINAS DO WIZARD ---
class WelcomePage(StyledPage):
    def __init__(self, parent=None):
        super().__init__("SISTEMAS ONLINE", "ONBOARDING OMNISCIENT AGENT PRO", parent)
        self.add_label("REGISTRO DO MESTRE")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Como devo chamá-lo? (Ex: Jhordan)")
        self.layout.addWidget(self.name_input)
        
        self.add_label("PERSONALIDADE")
        self.personality = QComboBox()
        # CORRIGIDO: Nomes conforme solicitado
        self.personality.addItems(["OMNI (Formal/Leal)", "H.A.L (Frio/Eficiente)", "Samantha (Amigável/Proativo)"])
        # CORRIGIDO: Design de seleção (Alto Contraste)
        self.personality.setStyleSheet("""
            QComboBox { 
                background: #1a1a2e; 
                color: #ffffff; 
                border: 2px solid #00d4ff; 
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QComboBox QListView {
                background-color: #05050a;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
        """)
        self.layout.addWidget(self.personality)
        self.layout.addStretch()

class IdentityPage(StyledPage):
    def __init__(self, parent=None):
        super().__init__("BIOMETRIA DE ELITE", "Mapeamento facial e assinatura de voz.")
        
        self.viewfinder = QLabel()
        self.viewfinder.setFixedSize(320, 240)
        self.viewfinder.setStyleSheet("background: #000; border: 2px solid #00d4ff; border-radius: 10px;")
        self.viewfinder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.viewfinder, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.face_instructions = QLabel("AGUARDANDO MAPEAMENTO")
        self.face_instructions.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 11px;")
        self.layout.addWidget(self.face_instructions, alignment=Qt.AlignmentFlag.AlignCenter)

        self.face_btn = QPushButton("INICIAR MAPEAMENTO FACIAL")
        self.face_btn.setFixedWidth(250)
        self.face_btn.clicked.connect(self.start_face_mapping)
        self.layout.addWidget(self.face_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.layout.addSpacing(10)
        
        v_frame = QFrame()
        v_frame.setStyleSheet("background: rgba(175, 82, 222, 10); border: 1px dashed #af52de; border-radius: 8px;")
        v_layout = QVBoxLayout(v_frame)
        
        lbl = QLabel("LEIA EM VOZ ALTA:")
        lbl.setStyleSheet("color: #af52de; font-size: 10px; font-weight: bold;")
        v_layout.addWidget(lbl)

        cal = QLabel('"Eu sou o mestre deste sistema. Omniscient, confirme minha identidade e ative os protocolos de segurança."')
        cal.setStyleSheet("color: white; font-style: italic; font-size: 11px;")
        cal.setWordWrap(True)
        v_layout.addWidget(cal)

        self.voice_status = QLabel("Aguardando registro (10s)...")
        self.voice_status.setStyleSheet("color: #888; font-size: 10px;")
        v_layout.addWidget(self.voice_status)
        
        self.voice_btn = QPushButton("GRAVAR ASSINATURA")
        self.voice_btn.setFixedWidth(200)
        self.voice_btn.setStyleSheet("background: #af52de; color: white;")
        self.voice_btn.clicked.connect(self.record_voice)
        v_layout.addWidget(self.voice_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.layout.addWidget(v_frame)

        self.cam_worker = CameraWorker()
        self.cam_worker.new_frame.connect(self._update_frame)
        self.cam_worker.error.connect(self._on_cam_error)
        # Inicia captura IMEDIATAMENTE ao entrar na página
        self.cam_worker.start_capture()

    @pyqtSlot(QImage)
    def _update_frame(self, img):
        self.face_instructions.setText("OLHE DIRETAMENTE PARA A LENTE")
        self.viewfinder.setPixmap(QPixmap.fromImage(img).scaled(self.viewfinder.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding))

    def _on_cam_error(self, err):
        self.face_instructions.setText(f"ERRO CÂMERA: {err}")
        self.face_instructions.setStyleSheet("color: #ff3b30; font-weight: bold;")

    def start_face_mapping(self):
        """Dispara sequência de fotos."""
        print("Setup: Iniciando mapeamento facial...")
        self.face_btn.setEnabled(False)
        self._take_sample("FRONTAL", "user_face_front.jpg")
        QTimer.singleShot(1500, lambda: self._take_sample("ESQUERDA", "user_face_left.jpg"))
        QTimer.singleShot(3000, lambda: self._take_sample("DIREITA", "user_face_right.jpg"))
        QTimer.singleShot(4000, self._finalize_face)

    def _take_sample(self, angle, filename):
        self.face_instructions.setText(f"POSICIONAMENTO: {angle}")
        # Efeito Flash
        self.viewfinder.setStyleSheet("background: #fff; border: 4px solid #fff; border-radius: 10px;")
        QTimer.singleShot(150, lambda: self.viewfinder.setStyleSheet("background: #000; border: 2px solid #00d4ff; border-radius: 10px;"))
        
        frame = self.cam_worker.get_snapshot()
        if frame is not None:
            import cv2
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory_db")
            os.makedirs(save_dir, exist_ok=True)
            cv2.imwrite(os.path.join(save_dir, filename), frame)

    def _finalize_face(self):
        self.face_instructions.setText("✅ MAPEAMENTO COMPLETO")
        self.face_instructions.setStyleSheet("color: #34c759; font-weight: bold;")
        self.viewfinder.setStyleSheet("background: #000; border: 4px solid #34c759; border-radius: 10px;")
        self.cam_worker.stop()

    def record_voice(self):
        self.voice_btn.setEnabled(False)
        self.voice_status.setText("GRAVANDO... FALE AGORA")
        self.voice_status.setStyleSheet("color: #ff3b30; font-weight: bold;")
        
        import pyaudio
        import wave
        
        def _rec():
            try:
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
                frames = []
                for _ in range(0, int(16000 / 1024 * 10)): # 10 seg
                    frames.append(stream.read(1024))
                stream.stop_stream()
                stream.close()
                p.terminate()
                
                os.makedirs("memory_db", exist_ok=True)
                with wave.open("memory_db/user_voice.wav", 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(frames))
                
                QMetaObject.invokeMethod(self.voice_status, "setText", Qt.ConnectionType.QueuedConnection, Q_ARG(str, "✅ ASSINATURA REGISTRADA"))
                QMetaObject.invokeMethod(self.voice_status, "setStyleSheet", Qt.ConnectionType.QueuedConnection, Q_ARG(str, "color: #34c759; font-weight: bold; border: none;"))
            except Exception as e:
                print(f"Erro na gravação: {e}")
            
        threading.Thread(target=_rec, daemon=True).start()

class BrainsPage(StyledPage):
    def __init__(self, parent=None):
        super().__init__("NÚCLEO NEURAL", "Configure suas conexões de nuvem.", parent)
        self.inputs = {}
        keys = [("DEEPSEEK_API_KEY", "DeepSeek API"), ("ANTHROPIC_API_KEY", "Anthropic Claude"), ("GOOGLE_GENERATIVE_AI_API_KEY", "Google Gemini Pro")]
        for env, label in keys:
            self.add_label(label)
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.layout.addWidget(edit)
            self.inputs[env] = edit
        self.layout.addStretch()

class ForgePage(StyledPage):
    def __init__(self, parent=None):
        super().__init__("FORJA DO DEV", "Integrações para automação total.")
        self.inputs = {}
        dev_keys = [("GITHUB_TOKEN", "GitHub Personal Token"), ("LINEAR_API_KEY", "Linear API Key")]
        for env, label in dev_keys:
            self.add_label(label)
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.layout.addWidget(edit)
            self.inputs[env] = edit
        self.layout.addStretch()

class SetupWizard(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OMNISCIENT ACTIVATION")
        self.setFixedSize(550, 750)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("MainFrame")
        self.container.setStyleSheet("""
            #MainFrame {
                background-color: rgba(10, 10, 20, 252);
                border: 2px solid #00d4ff;
                border-radius: 20px;
            }
            QPushButton {
                background-color: #00d4ff;
                color: black;
                font-weight: 800;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Avenir Next';
                border: none;
            }
            QPushButton:hover { background-color: #00f0ff; }
            QLineEdit {
                background: #111111;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-family: 'Menlo';
            }
        """)
        
        self.cont_layout = QVBoxLayout(self.container)
        self.cont_layout.setContentsMargins(0, 0, 0, 20)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #00d4ff; } background: #111; border: none;")
        self.progress.setTextVisible(False)
        self.cont_layout.addWidget(self.progress)
        
        header = QHBoxLayout()
        header.addStretch()
        close = QPushButton("×")
        close.setFixedSize(30, 30)
        close.setStyleSheet("background: transparent; color: #555; font-size: 24px;")
        close.clicked.connect(self.reject)
        header.addWidget(close)
        header.setContentsMargins(0, 5, 15, 0)
        self.cont_layout.addLayout(header)

        self.stack = QStackedWidget()
        self.p1 = WelcomePage()
        self.p2 = IdentityPage()
        self.p3 = BrainsPage()
        self.p4 = ForgePage()
        for p in [self.p1, self.p2, self.p3, self.p4]: self.stack.addWidget(p)
        self.cont_layout.addWidget(self.stack)
        
        nav = QHBoxLayout()
        nav.setContentsMargins(40, 0, 40, 30)
        self.btn_back = QPushButton("ANTERIOR")
        self.btn_back.setStyleSheet("background: #222; color: #888;")
        self.btn_next = QPushButton("PRÓXIMO >")
        self.btn_back.clicked.connect(self.prev_page); self.btn_next.clicked.connect(self.next_page)
        nav.addWidget(self.btn_back); nav.addSpacing(20); nav.addWidget(self.btn_next)
        self.cont_layout.addLayout(nav)
        
        self.main_layout.addWidget(self.container)
        self._drag_pos = None
        self.update_ui()

    def update_ui(self):
        idx = self.stack.currentIndex()
        self.progress.setValue(int(((idx+1)/4)*100))
        self.btn_back.setVisible(idx > 0)
        self.btn_next.setText("ATIVAR SISTEMA" if idx == 3 else "PRÓXIMO >")
        self.btn_next.setStyleSheet("background: #34c759; color: black;" if idx == 3 else "background: #00d4ff; color: black;")

    def next_page(self):
        if self.stack.currentIndex() < 3:
            self.stack.setCurrentIndex(self.stack.currentIndex() + 1)
            self.update_ui()
        else: self.finish()

    def prev_page(self):
        self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self.update_ui()

    def finish(self):
        print("SetupWizard: Finalizando...")
        env = [f"USER_NAME={self.p1.name_input.text() or 'Mestre'}"]
        for k, v in self.p3.inputs.items(): env.append(f"{k}={v.text()}")
        for k, v in self.p4.inputs.items(): env.append(f"{k}={v.text()}")
        with open(".env", "w") as f: f.write("\n".join(env))
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event): self._drag_pos = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    SetupWizard().show()
    sys.exit(app.exec())
