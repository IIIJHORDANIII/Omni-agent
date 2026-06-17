import os
import threading
import wave
import subprocess
import time
import re
from pathlib import Path
from piper.voice import PiperVoice

class PiperService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PiperService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path=None):
        if self._initialized:
            return
            
        # Default paths
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models/piper")
        self.model_path = model_path or os.path.join(base_path, "pt_BR-faber-medium.onnx")
        
        self.is_speaking = False
        self.current_playback_process = None
        self.status_callback = None
        
        try:
            print(f"Iniciando Piper TTS com modelo: {self.model_path}")
            if not os.path.exists(self.model_path):
                print(f"AVISO: Arquivo do modelo Piper não encontrado em {self.model_path}")
                self.voice = None
            else:
                self.voice = PiperVoice.load(self.model_path)
                print("Piper TTS carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar Piper: {e}")
            self.voice = None
            
        self._initialized = True

    def stop_speaking(self):
        """Interrompe a fala atual."""
        if self.current_playback_process:
            try:
                self.current_playback_process.terminate()
            except:
                pass
            self.current_playback_process = None

    def speak(self, text):
        """Fala o texto usando Piper TTS em Português."""
        if not text or not self.voice:
            if not self.voice:
                print("Piper não inicializado. Não é possível falar.")
            return

        self.stop_speaking()

        def _speak():
            try:
                # Limpa o texto para uma fala natural
                clean_text = re.sub(r'\[.*?\]', '', text) 
                clean_text = re.sub(r'[*#_`]', '', clean_text)
                clean_text = clean_text.strip()
                if not clean_text: return

                self.is_speaking = True
                if self.status_callback: self.status_callback("SPEAKING", True)

                # Salva em arquivo temporário para reprodução
                tmp_dir = os.path.expanduser("~/Library/Caches/AndersAgent")
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_path = os.path.join(tmp_dir, f"piper_{int(time.time())}.wav")

                print(f"Piper: Gerando áudio para: {clean_text[:30]}...")
                with wave.open(tmp_path, "wb") as wav_file:
                    self.voice.synthesize_wav(clean_text, wav_file)

                if os.path.exists(tmp_path):
                    try:
                        # Usa afplay para reprodução assíncrona fácil no macOS
                        self.current_playback_process = subprocess.Popen(["afplay", tmp_path])
                        self.current_playback_process.wait()
                        self.current_playback_process = None
                    finally:
                        try:
                            os.remove(tmp_path)
                        except:
                            pass

            except Exception as e:
                print(f"Erro no Piper TTS: {e}")
            finally:
                self.is_speaking = False
                if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()

    def set_status_callback(self, callback):
        self.status_callback = callback
