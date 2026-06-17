from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot


class PermissionGate(QWidget):
    confirmed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(340, 170)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 28, 30, 0.95);
                border: 0.5px solid rgba(255, 59, 48, 0.4);
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.label = QLabel("Ação crítica solicitada. Você permite?")
        self.label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.92);
            font-size: 13px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
            font-weight: 500;
        """)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_deny = QPushButton("Negar")
        self.btn_deny.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.85);
                font-weight: 500;
                border-radius: 8px;
                padding: 10px 20px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 13px;
                border: 0.5px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); }
        """)
        self.btn_deny.clicked.connect(lambda: self._respond(False))

        self.btn_allow = QPushButton("Permitir")
        self.btn_allow.setStyleSheet("""
            QPushButton {
                background-color: #ff453a;
                color: white;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 20px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #d63a2e; }
        """)
        self.btn_allow.clicked.connect(lambda: self._respond(True))

        btn_layout.addWidget(self.btn_deny)
        btn_layout.addWidget(self.btn_allow)

        layout.addWidget(self.label)
        layout.addLayout(btn_layout)

        main_layout.addWidget(self.container)
        self.hide()

    @pyqtSlot(str)
    def request_permission(self, action_desc):
        self.label.setText(f"<b>Ação Crítica:</b><br>{action_desc}<br><br>Você permite?")
        self.show()
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _respond(self, granted):
        self.hide()
        self.confirmed.emit(granted)
