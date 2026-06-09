import os
import threading
import subprocess
import time
import re
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ElevenLabsService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if self.api_key:
            self.client = ElevenLabs(api_key=self.api_key)
        else:
            self.client = None
            print("AVISO: ELEVENLABS_API_KEY não encontrada no .env")
            
        self.is_speaking = False
        self.current_playback_process = None
        self.status_callback = None
        
        # ID da voz do Cid Moreira (ou uma similar se não encontrada)
        # Nota: O usuário deve ter adicionado a voz à biblioteca dele.
        # Caso contrário, usaremos uma voz masculina profunda padrão.
        self.voice_id = "CidMoreira_ID_Placeholder" 
        self.model_id = "eleven_multilingual_v2"
            
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
        """Fala o texto usando ElevenLabs (Cinema Quality)."""
        if not text or not self.client:
            return

        self.stop_speaking()

        def _speak():
            try:
                # Limpa o texto
                clean_text = re.sub(r'\[.*?\]', '', text) 
                clean_text = re.sub(r'[*#_`]', '', clean_text)
                clean_text = clean_text.strip()
                if not clean_text: return

                self.is_speaking = True
                if self.status_callback: self.status_callback("SPEAKING", True)

                # Gera o áudio via ElevenLabs
                print(f"ElevenLabs: Gerando voz de cinema...")
                
                # Tenta buscar a voz do Cid Moreira na conta do usuário
                voice_to_use = "Josh" # Fallback para uma voz masculina forte
                try:
                    voices = self.client.voices.get_all()
                    for v in voices.voices:
                        if "Cid" in v.name or "Moreira" in v.name:
                            voice_to_use = v.voice_id
                            print(f"ElevenLabs: Voz do {v.name} encontrada!")
                            break
                except:
                    # Se não tiver permissão de leitura, usa o fallback Josh
                    pass

                audio_stream = self.client.text_to_speech.convert(
                    text=clean_text,
                    voice_id=voice_to_use,
                    model_id=self.model_id,
                    output_format="mp3_44100_128"
                )

                # Salva em arquivo temporário
                tmp_dir = os.path.expanduser("~/Library/Caches/OmniscientAgent")
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_path = os.path.join(tmp_dir, f"eleven_{int(time.time())}.mp3")

                with open(tmp_path, "wb") as f:
                    for chunk in audio_stream:
                        if chunk:
                            f.write(chunk)

                if os.path.exists(tmp_path):
                    self.current_playback_process = subprocess.Popen(["afplay", tmp_path])
                    self.current_playback_process.wait()
                    self.current_playback_process = None
                    os.remove(tmp_path)

            except Exception as e:
                print(f"Erro no ElevenLabs TTS: {e}")
            finally:
                self.is_speaking = False
                if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()
