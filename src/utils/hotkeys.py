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
    spotlight_requested = pyqtSignal()
    # Track Command key timestamps for double press
    _last_cmd_time = 0.0
    _cmd_press_interval = 0.4  # seconds (adjustable)
    _cmd_press_count = 0
    chat_requested = pyqtSignal()
    voice_requested = pyqtSignal()
    spotlight_requested = pyqtSignal()
    # Track Command key timestamps for double press
    _last_cmd_time = 0.0
    _cmd_press_interval = 0.4  # seconds (adjustable)
    _cmd_press_count = 0
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

        # Disabled chat shortcut (Shift+Cmd+O) – no longer used
        self.chat_target = set()
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

        # Chat shortcut disabled – no action
        # Spotlight shortcut: Double tap Cmd
        is_current_key_cmd = k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)
        if is_current_key_cmd:
            import time
            now = time.time()
            if now - self._last_cmd_time <= self._cmd_press_interval:
                self._cmd_press_count += 1
            else:
                self._cmd_press_count = 1
            self._last_cmd_time = now
            if self._cmd_press_count == 2:
                print("Spotlight shortcut detected!")
                self.spotlight_requested.emit()
                self._cmd_press_count = 0
                self.current_keys.clear()

        # Voice shortcut: Cmd + Shift + Enter
        has_cmd = any(k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r) for k in self.current_keys)
        has_shift = any(k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r) for k in self.current_keys)
        has_enter = keyboard.Key.enter in self.current_keys
        
        if has_cmd and has_shift and has_enter:
            print("Atalho de Voz detectado!")
            self.voice_requested.emit()
            # Clear keys to prevent rapid repeated firings
            self.current_keys.clear()

    def on_release(self, key):
        keyboard = _get_keyboard()
        if keyboard is None:
            return

        k = key
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())

        if k in self.current_keys:
            self.current_keys.remove(k)
