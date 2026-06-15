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
            self.amplitude_callback = None # Para notificar UI com nível de áudio em tempo real
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
            self.active_session_id = 0
            self.abort_listen = False
            self.is_listening_active = False # Evita que o processador de wake word roube áudio do listen()
            
            # Modelo Whisper (Transcrição)
            self.whisper_model = "mlx-community/whisper-large-v3-turbo"
            
            # Wake Word buffer
            self.wake_word_window = []
            self.window_seconds = 2.5
            self.samples_needed = int(self.RATE * self.window_seconds)
            self.is_continuous_mode = False # Nova flag para mãos-livres
            self._initialized = True

            # Registro no Arbiter
            from core.model_arbiter import arbiter
            arbiter.register_unloader("WHISPER", self.unload_model)

    def unload_model(self):
        """No MLX Whisper, o modelo é frequentemente carregado sob demanda, 
        mas aqui limpamos referências se houver."""
        if hasattr(self, 'whisper_model'):
            print("VoiceService: Descarregando Whisper da RAM...")
            # Como mlx_whisper.transcribe aceita o path, 
            # não mantemos um objeto model pesado persistente.
            pass

    def toggle_continuous_mode(self, enabled=None):
        """Alterna ou define o estado do modo de escuta contínua."""
        if enabled is None:
            self.is_continuous_mode = not self.is_continuous_mode
        else:
            self.is_continuous_mode = enabled
        print(f"🎤 Voz: Modo Contínuo {'ATIVADO' if self.is_continuous_mode else 'DESATIVADO'}")
        return self.is_continuous_mode

    @property
    def is_speaking(self):
        # Prioridade para o motor Piper se estiver em uso
        if hasattr(self, 'piper') and self.use_piper:
            return self.piper.is_speaking
        # Prioridade para o motor Kokoro se estiver em uso
        if hasattr(self, 'kokoro') and self.use_kokoro:
            return self.kokoro.is_speaking
        return getattr(self, "_is_speaking_internal", False)

    @is_speaking.setter
    def is_speaking(self, value):
        self._is_speaking_internal = value

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        mx.set_default_stream(mx.default_stream(mx.gpu))

    def start_listening_mode(self):
        """Inicia as threads de áudio sem ativar o loop de wake word."""
        if not hasattr(self, 'threads_started'):
            threading.Thread(target=self._audio_collector, daemon=True).start()
            threading.Thread(target=self._audio_processor, daemon=True).start()
            threading.Thread(target=self._global_audio_watchdog, daemon=True).start()
            self.threads_started = True

    def start_wake_word_detection(self, callback=None):
        if callback:
            self.on_wake_word_detected = callback
        
        self.start_listening_mode()
        threading.Thread(target=self._run_wake_word_loop, daemon=True).start()

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
                
                # Notifica a UI com o nível de áudio (para ondas animadas)
                if self.amplitude_callback:
                    try:
                        self.amplitude_callback(energy)
                    except Exception:
                        pass
                
                self.last_audio_time = time.time()
            except Exception as e:
                print(f"Erro na coleta de áudio: {e}")
                self._reset_stream()
                time.sleep(0.5)

    def _audio_processor(self):
        """Esvazia o buffer de áudio continuamente."""
        while self.running:
            # Se a escuta ativa estiver ligada, deixamos o áudio no buffer para o listen()
            if self.is_listening_active:
                time.sleep(0.1)
                continue

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
                                from core.model_arbiter import arbiter
                                arbiter.request_model("WHISPER")
                                
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
                                        # Variações fonéticas de "Omni" e comandos de interrupção
                                        omni_variants = ["omni", "omini", "homni", "ômine", "homeni", "homine", "amni", "omne", "ominy", "omyni"]
                                        stop_keywords = ["chega", "para", "parar", "silêncio", "stop", "quieto", "cala a boca"]
                                        
                                        words_in_text = re.sub(r'[^\w\s]', '', text).split()

                                        is_omni = any(kw in words_in_text for kw in omni_variants)
                                        is_stop = any(kw in words_in_text for kw in stop_keywords)

                                        if is_omni or is_stop:
                                            print(f"WAKE WORD/STOP DETECTADA: [{text}]")
                                            
                                            # BARGE-IN: Cala a boca imediatamente
                                            self.stop_speaking()
                                            
                                            # Se for apenas um comando de "chega", não precisamos processar como comando de voz complexo
                                            # Mas para manter a consistência, deixamos o fluxo seguir, 
                                            # o LLM saberá responder "Ok" e parar.
                                            
                                            if self.on_wake_word_detected:
                                                self.on_wake_word_detected()
                                                
                                            time.sleep(2.0)

                        except Exception as e:
                            print(f"Erro na transcrição Wake Word: {e}")
                
                last_process_time = time.time()
            time.sleep(0.1)

    def listen(self, continuous_mode=False):
        """Escuta um comando completo. Se continuous_mode=True, escuta imediatamente sem pre-buffer."""
        print("Ouvindo comando...")
        self.is_listening_active = True
        self.abort_listen = False # Reset para nova escuta
        start_time = time.time()
        recorded_audio = []
        silence_start = None
        max_duration = 8 
        energy_threshold = 0.010 
        
        silence_pad = [0.0] * int(self.RATE * 0.1)
        
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
            if self.abort_listen:
                print("Escuta interrompida por nova Wake Word.")
                return None

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
            
            if silence_start and (time.time() - silence_start > 0.5):
                break
            time.sleep(0.01) 
            
        if self.abort_listen: 
            self.is_listening_active = False
            return None
        
        recorded_audio.extend(silence_pad)
        
        # Filtro de ruído curto
        if not recorded_audio or len(recorded_audio) < self.RATE * 0.8: 
            self.is_listening_active = False
            return None
        
        print("Sintonizando voz...")
        self._ensure_stream()
        try:
            with mx.stream(mx.default_stream(mx.gpu)):
                from core.model_arbiter import arbiter
                arbiter.request_model("WHISPER")
                
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
                self.is_listening_active = False
                return final_text
        except Exception as e:
            print(f"Erro na transcrição: {e}")
            self.is_listening_active = False
            return None

    def stop_speaking(self):
        """Interrompe a fala de todos os motores imediatamente."""
        self.active_session_id += 1
        self.abort_listen = True
        
        # Interrompe Piper
        if hasattr(self, 'piper'):
            self.piper.stop_speaking()

        # Interrompe Kokoro
        if hasattr(self, 'kokoro'):
            self.kokoro.stop_speaking()
            
        try:
            # killall é a forma mais segura no macOS de parar o 'say' instantaneamente
            subprocess.run(["killall", "say"], capture_output=True)
        except:
            pass
        self.current_playback_process = None
        self.is_speaking = False

    def speak(self, text):
        """Fala o texto usando a voz nativa do macOS (Siri Masculino) conforme preferência do usuário."""
        if not text: return
            
        # Sinaliza sessão ativa
        self.is_speaking = True
        session_at_request = self.active_session_id
        
        # O usuário prefere a voz masculina nativa (Siri/Daniel/Eddy)
        # Desativamos Piper e Kokoro para respeitar a preferência por naturalidade nativa
        self._speak_native(text, session_at_request)

    def _speak_native(self, text, session_at_request):
        def _speak():
            # Lock para evitar que múltiplas falas se sobreponham
            with self.speaking_lock:
                if session_at_request != self.active_session_id: return

                try:
                    self.is_speaking = True
                    if self.status_callback: self.status_callback("SPEAKING", True)
                    
                    # Limpeza agressiva para fala fluída (Filtro Anti-Pensamento v2)
                    clean_text = re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
                    # Caso a tag não tenha sido fechada
                    if "<think>" in clean_text.lower():
                        clean_text = clean_text.lower().split("<think>")[0]
                    
                    # Remove prefixos comuns de raciocínio
                    clean_text = re.sub(r'^(Pensamento|Raciocínio|Thought|Análise):.*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
                    
                    clean_text = re.sub(r'[*#_`~]', '', clean_text)
                    clean_text = re.sub(r'\[.*?\]', '', clean_text).strip()
                    
                    if not clean_text or len(clean_text) < 2: return

                    # Usamos o comando 'say' sem o parâmetro -v para respeitar a voz padrão do sistema
                    # O usuário deve selecionar 'Siri Masculino' nas Configurações do macOS -> Acessibilidade -> Conteúdo Falado
                    self.current_playback_process = subprocess.Popen(["say", "--", clean_text])
                    self.current_playback_process.wait()
                    self.current_playback_process = None
                except Exception as e:
                    print(f"ERRO VOZ NATIVO: {e}")
                finally:
                    self.is_speaking = False
                    if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()
