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
            background-color: rgba(20, 20, 25, 230);
            border: 2px solid #af52de;
            border-radius: 15px;
        """)
        
        layout = QVBoxLayout(self.container)
        
        self.title = QLabel("Sugestão do Ghost Programmer")
        self.title.setStyleSheet("color: #af52de; font-weight: bold; font-size: 12px;")
        
        self.description = QLabel("Descrição da melhoria...")
        self.description.setStyleSheet("color: white; font-size: 11px;")
        self.description.setWordWrap(True)
        
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setStyleSheet("""
            background-color: #4cd964; color: black; font-weight: bold; border-radius: 5px; padding: 5px;
        """)
        self.btn_apply.clicked.connect(self._on_apply)
        
        self.btn_ignore = QPushButton("Ignorar")
        self.btn_ignore.setStyleSheet("""
            background-color: #ff3b30; color: white; font-weight: bold; border-radius: 5px; padding: 5px;
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
