import threading
from PyQt6.QtCore import QObject, pyqtSignal

# pynput importado sob demanda para evitar SIGTRAP no macOS
# quando não há permissões de acessibilidade
_keyboard = None

def _get_keyboard():
    global _keyboard
    if _keyboard is None:
        try:
            from pynput import keyboard
            _keyboard = keyboard
        except Exception as e:
            print(f"Hotkeys: pynput indisponível: {e}")
    return _keyboard


class GlobalHotkeyHandler(QObject):
    chat_requested = pyqtSignal()
    voice_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_keys = set()
        self._listener = None

    def start(self):
        keyboard = _get_keyboard()
        if keyboard is None:
            print("Hotkeys: pynput não disponível, atalhos desabilitados.")
            return

        self.chat_target = {
            keyboard.Key.cmd,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char('o')
        }
        self.voice_target = {
            keyboard.Key.cmd,
            keyboard.Key.shift,
            keyboard.Key.enter
        }

        def _run():
            print("Iniciando Listener de Teclado Nativo...")
            try:
                with keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release
                ) as listener:
                    self._listener = listener
                    listener.join()
            except Exception as e:
                print(f"Hotkeys: Erro no listener: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def on_press(self, key):
        keyboard = _get_keyboard()
        if keyboard is None:
            return

        k = key
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())

        self.current_keys.add(k)

        if hasattr(self, 'chat_target') and all(tk in self.current_keys for tk in self.chat_target):
            print("Atalho de Chat detectado!")
            self.chat_requested.emit()

        if hasattr(self, 'voice_target') and all(tk in self.current_keys for tk in self.voice_target):
            print("Atalho de Voz detectado!")
            self.voice_requested.emit()

    def on_release(self, key):
        keyboard = _get_keyboard()
        if keyboard is None:
            return

        k = key
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())

        if k in self.current_keys:
            self.current_keys.remove(k)
