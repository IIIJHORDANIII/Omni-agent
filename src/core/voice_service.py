import threading
import os
import subprocess
import numpy as np
import re
import time
import pyaudio
import mlx_whisper
import mlx.core as mx
from queue import Queue

class VoiceService:
    _instance = None
    _lock = threading.Lock()
    _thread_local = threading.local()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VoiceService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, on_wake_word_detected=None):
        with self._lock:
            if self._initialized: return
            self._is_speaking_internal = False 
            self.on_wake_word_detected = on_wake_word_detected
            self.status_callback = None # Para notificar início/fim de fala
            self.running = True
            self.audio_lock = threading.Lock()
            self.speaking_lock = threading.Lock() # Lock exclusivo para saída de voz
            
            # Configurações de Áudio
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.RATE = 16000
            self.CHUNK = 1024
            
            # Inicializa PyAudio de forma persistente
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=self.FORMAT,
                                    channels=self.CHANNELS,
                                    rate=self.RATE,
                                    input=True,
                                    frames_per_buffer=self.CHUNK)
            
            self.audio_buffer = Queue()
            self.last_audio_time = time.time() 
            
            # Motor de Voz: Nativo macOS (Siri)
            self.voice = "Siri" # Tenta usar a voz da Siri
            self.current_playback_process = None
            
            # Modelo Whisper (Transcrição)
            self.whisper_model = "mlx-community/whisper-large-v3-turbo"
            
            # Wake Word buffer
            self.wake_word_window = []
            self.window_seconds = 2.5
            self.samples_needed = int(self.RATE * self.window_seconds)
            self._initialized = True

    @property
    def is_speaking(self):
        return getattr(self, "_is_speaking_internal", False)

    @is_speaking.setter
    def is_speaking(self, value):
        self._is_speaking_internal = value

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        mx.set_default_stream(mx.default_stream(mx.gpu))

    def start_wake_word_detection(self, callback=None):
        if callback:
            self.on_wake_word_detected = callback
        
        threading.Thread(target=self._audio_collector, daemon=True).start()
        threading.Thread(target=self._audio_processor, daemon=True).start()
        threading.Thread(target=self._run_wake_word_loop, daemon=True).start()
        threading.Thread(target=self._global_audio_watchdog, daemon=True).start()

    def _global_audio_watchdog(self):
        """Monitora se o áudio parou de fluir por inatividade de hardware."""
        while self.running:
            if time.time() - self.last_audio_time > 10.0:
                self._reset_stream()
                self.last_audio_time = time.time()
            time.sleep(5)

    def _audio_collector(self):
        """Coleta áudio do microfone continuamente (mesmo falando, para barge-in)."""
        while self.running:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                # Removemos a restrição de self.is_speaking para permitir barge-in
                
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                energy = np.sqrt(np.mean(audio_np**2))
                if energy > 0.002:
                    self.audio_buffer.put(data)
                
                self.last_audio_time = time.time()
            except Exception as e:
                print(f"Erro na coleta de áudio: {e}")
                self._reset_stream()
                time.sleep(0.5)

    def _audio_processor(self):
        """Esvazia o buffer de áudio continuamente."""
        while self.running:
            while not self.audio_buffer.empty():
                try:
                    chunk = self.audio_buffer.get_nowait()
                    audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                    with self.audio_lock:
                        self.wake_word_window.extend(audio_np.tolist())
                        if len(self.wake_word_window) > self.samples_needed:
                            self.wake_word_window = self.wake_word_window[-self.samples_needed:]
                except:
                    break
            time.sleep(0.05)

    def _reset_stream(self):
        """Reinicia o stream de áudio."""
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = self.p.open(format=self.FORMAT,
                                    channels=self.CHANNELS,
                                    rate=self.RATE,
                                    input=True,
                                    frames_per_buffer=self.CHUNK)
        except Exception as e:
            print(f"Voz: Falha crítica ao reiniciar áudio: {e}")

    def _run_wake_word_loop(self):
        print("Monitorando Wake Word (Whisper Turbo)...")
        last_process_time = time.time()
        self._ensure_stream()
        
        while self.running:
            if time.time() - last_process_time > 1.2:
                audio_data = None
                with self.audio_lock:
                    if len(self.wake_word_window) >= self.RATE:
                        audio_data = np.array(self.wake_word_window, dtype=np.float32)
                
                if audio_data is not None:
                    with mx.stream(mx.default_stream(mx.gpu)):
                        try:
                            energy = np.sqrt(np.mean(audio_data**2))
                            if energy > 0.012:
                                # Usa getattr para segurança caso o modelo não tenha sido carregado
                                model = getattr(self, "whisper_model", "mlx-community/whisper-large-v3-turbo")
                                result = mlx_whisper.transcribe(
                                    audio_data, 
                                    path_or_hf_repo=model,
                                    language="pt"
                                )
                                text = result["text"].lower().strip()
                                mx.clear_cache()
                                
                                if text:
                                    words = text.split()
                                    if len(words) > 3 and len(set(words)) / len(words) < 0.4:
                                        last_process_time = time.time()
                                        continue

                                    if len(text) > 2 and "legendas" not in text:
                                        # Variações fonéticas de "Omni" no Whisper em PT-BR
                                        keywords = ["omni", "omini", "homni", "ômine", "homeni", "homine", "amni", "omne", "ominy", "omyni"]
                                        words_in_text = re.sub(r'[^\w\s]', '', text).split()

                                        if any(kw in words_in_text for kw in keywords):
                                            print(f"WAKE WORD DETECTADA: [{text}]")
                                            
                                            # BARGE-IN: Se estava falando, cala a boca imediatamente
                                            if self.is_speaking:
                                                self.stop_speaking()
                                            
                                            # Não falamos "Sim?". Apenas emitimos o sinal de que ouvimos.
                                            if self.on_wake_word_detected:
                                                self.on_wake_word_detected()
                                                
                                            # NÃO limpamos o wake_word_window aqui. Deixamos ele vazar 
                                            # para o `listen()` para que o comando comece do início.
                                            time.sleep(2.0)

                        except Exception as e:
                            print(f"Erro na transcrição Wake Word: {e}")
                
                last_process_time = time.time()
            time.sleep(0.1)

    def listen(self, continuous_mode=False):
        """Escuta um comando completo. Se continuous_mode=True, escuta imediatamente sem pre-buffer."""
        print("Ouvindo comando...")
        start_time = time.time()
        recorded_audio = []
        silence_start = None
        max_duration = 8 
        energy_threshold = 0.010 
        
        silence_pad = [0.0] * int(self.RATE * 0.3)
        
        with self.audio_lock:
            # Se não estamos em modo contínuo, reaproveitamos o áudio que ativou a wake word
            # Isso garante que a frase "Omni abre o youtube" não perca o "abre"
            if not continuous_mode and self.wake_word_window:
                recorded_audio.extend(self.wake_word_window)
            
            # Esvazia a fila atual para a gravação principal
            while not self.audio_buffer.empty():
                try:
                    self.audio_buffer.get_nowait()
                except:
                    break
            self.wake_word_window = []

        while time.time() - start_time < max_duration:
            while not self.audio_buffer.empty():
                chunk = self.audio_buffer.get()
                audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                energy = np.sqrt(np.mean(audio_np**2))
                
                if energy > 0.005:
                    recorded_audio.extend(audio_np.tolist())
                
                if energy < energy_threshold:
                    if silence_start is None: silence_start = time.time()
                else:
                    silence_start = None
            
            if silence_start and (time.time() - silence_start > 1.2):
                break
            time.sleep(0.01) 
            
        recorded_audio.extend(silence_pad)
        
        # Filtro de ruído curto
        if not recorded_audio or len(recorded_audio) < self.RATE * 0.8: 
            return None
        
        print("Sintonizando voz...")
        self._ensure_stream()
        try:
            with mx.stream(mx.default_stream(mx.gpu)):
                audio_data = np.array(recorded_audio, dtype=np.float32)
                model = getattr(self, "whisper_model", "mlx-community/whisper-large-v3-turbo")
                result = mlx_whisper.transcribe(
                    audio_data, 
                    path_or_hf_repo=model,
                    language="pt"
                )
                final_text = result["text"].strip()
                final_text = re.sub(r'[^\w\sÀ-ÿ.,!?]', '', final_text)
                mx.clear_cache()
                
                # Se só capturou a wake word isolada, ignora
                keywords = ["jarvis", "agente", "computador", "omni", "omniscient"]
                clean_verify = re.sub(r'[^\w\s]', '', final_text.lower()).strip()
                if clean_verify in keywords:
                    return None
                    
                if len(final_text) < 2: return None
                print(f"Comando completo: {final_text}")
                return final_text
        except Exception as e:
            print(f"Erro na transcrição: {e}")
            return None

    def stop_speaking(self):
        """Interrompe a fala nativa imediatamente."""
        if self.current_playback_process:
            try:
                subprocess.run(["killall", "say"], capture_output=True)
            except:
                pass
            self.current_playback_process = None
        self.is_speaking = False

    def speak(self, text):
        """Fala o texto usando a voz padrão do sistema (que o usuário definiu como Siri)."""
        if not text: 
            print("DEBUG VOZ: Texto vazio recebido, ignorando.")
            return
        
        def _speak():
            # Lock para evitar que múltiplas falas se sobreponham
            print(f"DEBUG VOZ: Tentando obter lock para falar...")
            with self.speaking_lock:
                try:
                    print(f"DEBUG VOZ: Preparando texto: {text[:50]}...")
                    # Limpeza ultra-agressiva para garantir que NADA técnico seja falado
                    clean_text = text
                    
                    # 1. Remove qualquer conteúdo entre tags <think> (mesmo que malformadas)
                    clean_text = re.sub(r'<think>.*?</think>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
                    clean_text = re.sub(r'.*?</think>', '', clean_text, flags=re.DOTALL | re.IGNORECASE) # Caso começou no pensamento
                    clean_text = re.sub(r'<think>.*', '', clean_text, flags=re.DOTALL | re.IGNORECASE) # Caso não fechou
                    clean_text = clean_text.replace('<think>', '').replace('</think>', '')
                    
                    # 2. Remove blocos de código markdown
                    clean_text = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
                    
                    # 3. Remove caracteres de formatação e colchetes (JSON/Tags)
                    clean_text = re.sub(r'[*#_`~]', '', clean_text)
                    clean_text = re.sub(r'\[.*?\]', '', clean_text)
                    clean_text = re.sub(r'\{.*?\}', '', clean_text)
                    
                    # 4. Remove termos técnicos de depuração que vazam
                    tech_terms = ['DEBUG', 'JSON', 'NEED_TRANSLATION', 'assistant', 'user', 'system']
                    for term in tech_terms:
                        clean_text = re.sub(rf'\b{term}\b', '', clean_text, flags=re.IGNORECASE)
                    
                    # 5. Humanização final
                    clean_text = clean_text.replace('UI', 'interface').strip()
                    
                    # Se após a limpeza o texto for curto demais ou puramente técnico, ignora
                    if not clean_text or len(clean_text) < 3: 
                        print("DEBUG VOZ: Texto descartado por ser puramente técnico ou vazio.")
                        return

                    self.is_speaking = True
                    if self.status_callback: self.status_callback("SPEAKING", True)

                    print(f"DEBUG VOZ: EXECUTANDO 'say {clean_text[:30]}...'")
                    
                    # No macOS, o comando 'say' é muito robusto. 
                    # Vamos rodar da forma mais simples possível.
                    process = subprocess.Popen(["say", clean_text])
                    process.wait()
                    
                    print(f"DEBUG VOZ: Finalizado com sucesso.")

                except Exception as e:
                    print(f"ERRO CRÍTICO VOZ: {e}")
                finally:
                    self.is_speaking = False
                    if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()
