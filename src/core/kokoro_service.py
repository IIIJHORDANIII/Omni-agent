import os
import threading
import soundfile as sf
import subprocess
import tempfile
import time
import re
from kokoro_onnx import Kokoro

class KokoroService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KokoroService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path=None, voices_path=None):
        if self._initialized:
            return
            
        # Default paths
        base_path = "/Users/pastorello/Documents/pessoal/agent/src/models/kokoro"
        self.model_path = model_path or os.path.join(base_path, "kokoro-v1.0.onnx")
        self.voices_path = voices_path or os.path.join(base_path, "voices.bin")
        
        self.is_speaking = False
        self.current_playback_process = None
        self.status_callback = None
        
        try:
            print(f"Iniciando Kokoro TTS com modelo: {self.model_path}")
            if not os.path.exists(self.model_path) or not os.path.exists(self.voices_path):
                print(f"AVISO: Arquivos do Kokoro não encontrados. Use o script de download.")
                self.kokoro = None
            else:
                self.kokoro = Kokoro(self.model_path, self.voices_path)
                print("Kokoro TTS carregado com sucesso (Offline).")
        except Exception as e:
            print(f"Erro ao carregar Kokoro: {e}")
            self.kokoro = None
            
        self._initialized = True

    def stop_speaking(self):
        """Interrompe a fala atual."""
        if self.current_playback_process:
            try:
                self.current_playback_process.terminate()
            except:
                pass
            self.current_playback_process = None

    def speak(self, text, voice="pm_alex", speed=1.0, lang="pt-br"):
        """Fala o texto usando Kokoro ONNX (Offline) em Português."""
        if not text or not self.kokoro:
            if not self.kokoro:
                print("Kokoro não inicializado. Não é possível falar.")
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

                # Gera o áudio via Kokoro em Português
                print(f"Kokoro: Gerando áudio (PT-BR) para: {clean_text[:30]}...")
                samples, sample_rate = self.kokoro.create(
                    clean_text, 
                    voice=voice, 
                    speed=speed, 
                    lang=lang
                )

                # Salva em arquivo temporário para reprodução
                tmp_dir = os.path.expanduser("~/Library/Caches/OmniscientAgent")
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_path = os.path.join(tmp_dir, f"kokoro_{int(time.time())}.wav")

                sf.write(tmp_path, samples, sample_rate)

                if os.path.exists(tmp_path):
                    # Usa afplay para reprodução assíncrona fácil no macOS
                    self.current_playback_process = subprocess.Popen(["afplay", tmp_path])
                    self.current_playback_process.wait()
                    self.current_playback_process = None
                    try:
                        os.remove(tmp_path)
                    except:
                        pass

            except Exception as e:
                print(f"Erro no Kokoro TTS: {e}")
            finally:
                self.is_speaking = False
                if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()

    def get_available_voices(self):
        if self.kokoro:
            return self.kokoro.get_voices()
        return []
