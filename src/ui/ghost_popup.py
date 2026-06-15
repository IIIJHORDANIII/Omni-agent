from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QFont


class DiffHighlighter(QSyntaxHighlighter):
    """Highlighter simples para diferencas (linhas verdes/vermelhas)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._diff_format_add = QTextCharFormat()
        self._diff_format_add.setForeground(QColor("#4cd964"))
        self._diff_format_add.setBackground(QColor("#1a3a1a"))

        self._diff_format_remove = QTextCharFormat()
        self._diff_format_remove.setForeground(QColor("#ff3b30"))
        self._diff_format_remove.setBackground(QColor("#3a1a1a"))

        self._diff_format_header = QTextCharFormat()
        self._diff_format_header.setForeground(QColor("#af52de"))
        self._diff_format_header.setFontWeight(700)

    def highlightBlock(self, text):
        if text.startswith("+") and not text.startswith("+++"):
            self.setFormat(0, len(text), self._diff_format_add)
        elif text.startswith("-") and not text.startswith("---"):
            self.setFormat(0, len(text), self._diff_format_remove)
        elif text.startswith("@@"):
            self.setFormat(0, len(text), self._diff_format_header)


class GhostPopup(QWidget):
    """
    Popup flutuante para o Ghost Programmer sugerir e aplicar correcoes.
    Exibe diff visual com diferenciacao de cores.
    """
    applied = pyqtSignal(str, str, str)  # file_path, old_text, new_text
    ignored = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_data = None

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.container = QFrame()
        self.container.setStyleSheet("""
            background-color: rgba(20, 20, 25, 235);
            border: 2px solid #af52de;
            border-radius: 15px;
        """)

        layout = QVBoxLayout(self.container)
        layout.setSpacing(6)

        # Header
        self.title = QLabel("Sugestao do Ghost Programmer")
        self.title.setStyleSheet("color: #af52de; font-weight: bold; font-size: 13px; padding: 4px;")
        layout.addWidget(self.title)

        # Descricao
        self.description = QLabel("Descricao da melhoria...")
        self.description.setStyleSheet("color: #ccc; font-size: 11px; padding: 2px 4px;")
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        # Arquivo alvo
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: #00d4ff; font-size: 10px; font-family: monospace; padding: 2px 4px;")
        layout.addWidget(self.file_label)

        # Area de diff
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setMaximumHeight(200)
        self.diff_view.setStyleSheet("""
            QTextEdit {
                background-color: #0d0d12;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                font-family: 'SF Mono', 'Menlo', monospace;
                font-size: 10px;
                padding: 6px;
            }
        """)
        self.diff_highlighter = DiffHighlighter(self.diff_view.document())
        layout.addWidget(self.diff_view)

        # Botoes
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setStyleSheet("""
            background-color: #4cd964; color: black; font-weight: bold;
            border-radius: 5px; padding: 6px 12px; font-size: 11px;
        """)
        self.btn_apply.clicked.connect(self._on_apply)

        self.btn_ignore = QPushButton("Ignorar")
        self.btn_ignore.setStyleSheet("""
            background-color: #ff3b30; color: white; font-weight: bold;
            border-radius: 5px; padding: 6px 12px; font-size: 11px;
        """)
        self.btn_ignore.clicked.connect(self._on_ignore)

        btn_layout.addWidget(self.btn_ignore)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        self.setFixedWidth(420)

    def show_suggestion(self, file_path, description, old_text, new_text):
        self.current_data = {
            "file": file_path,
            "old": old_text,
            "new": new_text
        }
        self.description.setText(description)
        self.file_label.setText(f"Arquivo: {file_path}")

        # Gera diff visual
        diff_text = self._generate_diff(old_text, new_text)
        self.diff_view.setPlainText(diff_text)

        self.adjustSize()

        # Posiciona no canto inferior direito
        screen = self.screen().geometry()
        self.move(
            screen.width() - self.width() - 20,
            screen.height() - self.height() - 60
        )
        self.show()

    def _generate_diff(self, old_text, new_text):
        """Gera um diff simples linha por linha."""
        old_lines = old_text.strip().split('\n') if old_text else []
        new_lines = new_text.strip().split('\n') if new_text else []

        diff = []
        diff.append("--- Original")
        diff.append("+++ Novo")
        diff.append("@")

        # Alinhamento simples por linha
        max_lines = max(len(old_lines), len(new_lines))
        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line is not None and new_line is not None:
                if old_line.strip() != new_line.strip():
                    diff.append(f"- {old_line}")
                    diff.append(f"+ {new_line}")
                else:
                    diff.append(f"  {old_line}")
            elif old_line is not None:
                diff.append(f"- {old_line}")
            elif new_line is not None:
                diff.append(f"+ {new_line}")

        return '\n'.join(diff)

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
