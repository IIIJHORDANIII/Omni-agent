import threading
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard

class GlobalHotkeyHandler(QObject):
    chat_requested = pyqtSignal()
    voice_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_keys = set()
        
        # Atalho para Chat: Command + Shift + O
        self.chat_target = {
            keyboard.Key.cmd,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char('o')
        }
        
        # Atalho para Voz: Command + Shift + Enter
        self.voice_target = {
            keyboard.Key.cmd,
            keyboard.Key.shift,
            keyboard.Key.enter
        }

    def on_press(self, key):
        # Normaliza a tecla para comparação
        k = key
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())
        
        self.current_keys.add(k)
        
        # Verifica atalho de Chat
        if all(tk in self.current_keys for tk in self.chat_target):
            print("Atalho de Chat detectado!")
            self.chat_requested.emit()
            
        # Verifica atalho de Voz
        if all(tk in self.current_keys for tk in self.voice_target):
            print("Atalho de Voz detectado!")
            self.voice_requested.emit()

    def on_release(self, key):
        k = key
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())
        
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
