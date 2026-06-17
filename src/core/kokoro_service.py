import os
import threading
import numpy as np
import sounddevice as sd
import time
import re
from queue import Queue
from kokoro_onnx import Kokoro

class KokoroService:
    """
    Serviço de Voz Realista usando Kokoro ONNX.
    Otimizado para Apple Silicon com streaming via fila thread-safe.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KokoroService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path=None, voices_path=None):
        if self._initialized: return
            
        # Caminhos dos modelos
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models/kokoro")
        self.model_path = model_path or os.path.join(base_path, "kokoro-v1.0.onnx")
        self.voices_path = voices_path or os.path.join(base_path, "voices.bin")
        
        self._is_speaking = False
        self._abort_playback = False
        self.status_callback = None
        self.amplitude_callback = None
        self.spectrum_callback = None
        self.playback_queue = Queue()
        self.running = True
        
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.voices_path):
                self.kokoro = Kokoro(self.model_path, self.voices_path)
                print("🧠 Kokoro TTS: Motor de voz ultra-realista ONLINE.")
                # Inicia a thread de processamento de áudio
                threading.Thread(target=self._playback_worker, daemon=True).start()
            else:
                print(f"⚠️ Kokoro TTS: Arquivos não encontrados em {base_path}. Fallback ativo.")
                self.kokoro = None
        except Exception as e:
            print(f"❌ Erro ao carregar Kokoro: {e}")
            self.kokoro = None
            
        self._initialized = True

    @property
    def is_speaking(self):
        return self._is_speaking or not self.playback_queue.empty()

    @is_speaking.setter
    def is_speaking(self, value):
        self._is_speaking = value

    def stop_speaking(self):
        """Interrompe a reprodução de áudio e limpa a fila imediatamente."""
        self._abort_playback = True
        # Limpa a fila
        while not self.playback_queue.empty():
            try:
                self.playback_queue.get_nowait()
            except:
                break
        
        try:
            sd.stop()
        except:
            pass
        self._is_speaking = False

    def _playback_worker(self):
        """Thread que consome a fila de áudio e reproduz sequencialmente."""
        while self.running:
            try:
                # Use timeout para permitir que a thread verifique self.running
                try:
                    item = self.playback_queue.get(timeout=1.0)
                except:
                    continue

                if item is None: 
                    self.playback_queue.task_done()
                    break # Sentinel para parar a thread
                
                samples, sample_rate = item
                self._is_speaking = True
                if self.status_callback: self.status_callback("SPEAKING", True)
                
                self._abort_playback = False
                try:
                    # Toca o áudio de forma não-bloqueante para podermos processar a amplitude
                    sd.play(samples, sample_rate)
                    
                    # Simulação de amplitude durante o playback
                    # Como sd.play é assíncrono, vamos calcular a energia por blocos
                    chunk_size = int(sample_rate * 0.05) # 50ms
                    for i in range(0, len(samples), chunk_size):
                        if self._abort_playback:
                            sd.stop()
                            break
                        
                        if self.amplitude_callback:
                            chunk = samples[i:i+chunk_size]
                            if len(chunk) > 0:
                                energy = np.sqrt(np.mean(chunk**2))
                                self.amplitude_callback(float(energy))
                        
                        time.sleep(0.045) # Um pouco menos que 50ms para manter o ritmo

                    # Aguarda o término real se necessário
                    sd.wait()
                except Exception as play_error:
                    print(f"⚠️ Erro ao iniciar playback: {play_error}")
                
                self.playback_queue.task_done()

            except Exception as e:
                print(f"⚠️ Erro no worker de voz: {e}")
            finally:
                if self.playback_queue.empty():
                    self._is_speaking = False
                    if self.status_callback: self.status_callback("SPEAKING", False)

    def __del__(self):
        self.running = False
        self.playback_queue.put(None)

    def speak(self, text, voice="af_bella", speed=1.1, lang="pt-br"):
        """Adiciona texto à fila para processamento e fala."""
        if not text or not self.kokoro: return

        from utils.tts_preprocessor import preprocess_for_tts

        # Limpeza de texto para fala natural + pronúncia bilingue
        clean_text = preprocess_for_tts(text)
        clean_text = clean_text.replace("UI", "interface").strip()
        
        if not clean_text or len(clean_text) < 2: return

        def _generate_and_enqueue():
            try:
                # Geração de Samples (Nativo Kokoro ONNX)
                samples, sample_rate = self.kokoro.create(
                    clean_text, 
                    voice=voice, 
                    speed=speed, 
                    lang=lang
                )
                self.playback_queue.put((samples, sample_rate))
            except Exception as e:
                print(f"⚠️ Erro ao gerar áudio Kokoro: {e}")

        # A geração do áudio ainda pode ser em thread para não travar o chamador (LLM stream)
        threading.Thread(target=_generate_and_enqueue, daemon=True).start()

    def get_available_voices(self):
        if self.kokoro:
            return self.kokoro.get_voices()
        return []
 
                    voice=voice, 
                    speed=speed, 
                    lang=lang
                )
                self.playback_queue.put((samples, sample_rate))
            except Exception as e:
                print(f"⚠️ Erro ao gerar áudio Kokoro: {e}")

        # A geração do áudio ainda pode ser em thread para não travar o chamador (LLM stream)
        threading.Thread(target=_generate_and_enqueue, daemon=True).start()

    def get_available_voices(self):
        if self.kokoro:
            return self.kokoro.get_voices()
        return []
