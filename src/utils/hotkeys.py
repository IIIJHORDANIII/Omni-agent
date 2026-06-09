import threading
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard

class GlobalHotkeyHandler(QObject):
    hotkey_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Usamos uma combinação simples sem o HotKey helper que está bugando
        self.current_keys = set()
        # Atalho: Command + Shift + O
        # No pynput para Mac:
        # <cmd> = keyboard.Key.cmd
        # <shift> = keyboard.Key.shift
        self.target_keys = {
            keyboard.Key.cmd,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char('o')
        }

    def on_press(self, key):
        # Normaliza a tecla para comparação
        k = getattr(key, 'char', key)
        if isinstance(k, str):
            k = keyboard.KeyCode.from_char(k.lower())
        
        self.current_keys.add(k)
        
        # Verifica se todas as teclas alvo estão pressionadas
        if all(tk in self.current_keys for tk in self.target_keys):
            print("Atalho detectado (Manual)!")
            self.hotkey_pressed.emit()

    def on_release(self, key):
        k = getattr(key, 'char', key)
        if isinstance(k, str):
            k = keyboard.KeyCode.from_char(k.lower())
        
        if k in self.current_keys:
            self.current_keys.remove(k)

    def start(self):
        def _run():
            print("Iniciando Listener de Teclado Nativo...")
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            ) as listener:
                listener.join()
        
        threading.Thread(target=_run, daemon=True).start()
