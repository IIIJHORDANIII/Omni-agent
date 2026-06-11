from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

class PermissionGate(QWidget):
    """
    Interface de segurança para confirmar ações críticas do Agente.
    """
    confirmed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(350, 180)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: 2px solid #ff4b4b;
                border-radius: 12px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            #btn_allow {
                background-color: #ff4b4b;
                color: white;
            }
            #btn_deny {
                background-color: #333;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        self.label = QLabel("O Agente solicitou uma ação crítica.\nVocê permite?")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        self.btn_deny = QPushButton("Negar")
        self.btn_deny.setObjectName("btn_deny")
        self.btn_deny.clicked.connect(lambda: self._respond(False))
        
        self.btn_allow = QPushButton("Permitir")
        self.btn_allow.setObjectName("btn_allow")
        self.btn_allow.clicked.connect(lambda: self._respond(True))
        
        btn_layout.addWidget(self.btn_deny)
        btn_layout.addWidget(self.btn_allow)
        
        layout.addWidget(self.label)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.hide()

    def request_permission(self, action_desc):
        self.label.setText(f"<b>Ação Crítica:</b><br>{action_desc}<br><br>Você permite?")
        self.show()
        # Centraliza na tela (aproximado)
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _respond(self, granted):
        self.hide()
        self.confirmed.emit(granted)
