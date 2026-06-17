from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

class GhostPopup(QWidget):
    """
    Popup flutuante para o Ghost Programmer sugerir e aplicar correções.
    """
    applied = pyqtSignal(str, str, str) # file_path, old_text, new_text
    ignored = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_data = None

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 28, 30, 0.92);
                border: 0.5px solid rgba(175, 82, 222, 0.4);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self.container)
        
        self.title = QLabel("Ghost Programmer")
        self.title.setStyleSheet("""
            color: #bf5af2;
            font-weight: 600;
            font-size: 13px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        
        self.description = QLabel("Descrição da melhoria...")
        self.description.setStyleSheet("""
            color: rgba(255, 255, 255, 0.75);
            font-size: 12px;
            font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
        """)
        self.description.setWordWrap(True)
        
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #34c759;
                color: white;
                font-weight: 600;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover { background-color: #2db84e; }
        """)
        self.btn_apply.clicked.connect(self._on_apply)
        
        self.btn_ignore = QPushButton("Ignorar")
        self.btn_ignore.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.85);
                font-weight: 500;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: '.AppleSystemUIFont', -apple-system, sans-serif;
                font-size: 12px;
                border: 0.5px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); }
        """)
        self.btn_ignore.clicked.connect(self._on_ignore)
        
        btn_layout.addWidget(self.btn_ignore)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addWidget(self.title)
        layout.addWidget(self.description)
        layout.addLayout(btn_layout)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        self.setFixedWidth(300)

    def show_suggestion(self, file_path, description, old_text, new_text):
        self.current_data = {
            "file": file_path,
            "old": old_text,
            "new": new_text
        }
        self.description.setText(description)
        self.adjustSize()
        
        # Posiciona no canto inferior direito
        screen = self.screen().geometry()
        self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 60)
        self.show()

    def _on_apply(self):
        if self.current_data:
            self.applied.emit(
                self.current_data["file"], 
                self.current_data["old"], 
                self.current_data["new"]
            )
        self.hide()

    def _on_ignore(self):
        self.ignored.emit()
        self.hide()
