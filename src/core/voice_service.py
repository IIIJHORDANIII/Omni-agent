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
            self.status_callback = None
            self.running = True
            self.audio_lock = threading.Lock()
            self.speaking_lock = threading.Lock()
            
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.RATE = 16000
            self.CHUNK = 1024
            
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=self.FORMAT,
                                    channels=self.CHANNELS,
                                    rate=self.RATE,
                                    input=True,
                                    frames_per_buffer=self.CHUNK)
            
            self.audio_buffer = Queue()
            self.last_audio_time = time.time() 
            
            self.voice = "Siri"
            self.current_playback_process = None
            self.active_session_id = 0
            self.abort_listen = False
            self.is_listening_active = False
            
            self.whisper_model = "mlx-community/whisper-large-v3-turbo"
            
            self.wake_word_window = []
            self.window_seconds = 2.5
            self.samples_needed = int(self.RATE * self.window_seconds)
            self.is_continuous_mode = False

            # Voiceprint: identificacao por voz
            self._voiceprint = None
            self._last_speaker = None
            self._last_similarity = 0.0

            self._initialized = True

            from core.model_arbiter import arbiter
            arbiter.register_unloader("WHISPER", self.unload_model)

    @property
    def voiceprint(self):
        if self._voiceprint is None:
            from core.voiceprint_service import VoiceprintService
            self._voiceprint = VoiceprintService()
        return self._voiceprint

    def unload_model(self):
        """No MLX Whisper, o modelo é frequentemente carregado sob demanda, 
        mas aqui limpamos referências se houver."""
        if hasattr(self, 'whisper_model'):
            print("VoiceService: Descarregando Whisper da RAM...")
            # Como mlx_whisper.transcribe aceita o path, 
            # não mantemos um objeto model pesado persistente.
            pass

    def toggle_continuous_mode(self, enabled=None):
        """Alterna ou define o estado do modo de escuta continua."""
        if enabled is None:
            self.is_continuous_mode = not self.is_continuous_mode
        else:
            self.is_continuous_mode = enabled
        print(f"Voz: Modo Continuo {'ATIVADO' if self.is_continuous_mode else 'DESATIVADO'}")
        return self.is_continuous_mode

    def enroll_voice(self, num_samples=5, duration_each=3):
        """
        Enrola a voz do usuario. Grava N amostras de D segundos cada.
        Retorna: True se sucesso, False caso contrario.
        """
        print(f"Voiceprint: Gravando {num_samples} amostras de {duration_each}s cada...")
        print("Fale uma frase curta e clara a cada vez. Aguarde o sinal.")

        samples = []
        for i in range(num_samples):
            print(f"  Amostra {i+1}/{num_samples}... grave AGORA")
            audio = self._record_audio(duration_each)
            if audio is not None and len(audio) > 0:
                samples.append(audio)
                print(f"  Amostra {i+1} capturada ({len(audio)/self.RATE:.1f}s)")
            else:
                print(f"  Amostra {i+1} falhou")

        if len(samples) < 2:
            print("Voiceprint: Amostras insuficientes.")
            return False

        success = self.voiceprint.register(samples)
        if success:
            print("Voiceprint: Perfil de voz registrado com sucesso!")
        else:
            print("Voiceprint: Falha no registro.")
        return success

    def _record_audio(self, duration_seconds):
        """Grava audio por N segundos e retorna numpy array."""
        import numpy as np
        frames = []
        for _ in range(0, int(self.RATE / self.CHUNK * duration_seconds)):
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
            except Exception:
                break

        if not frames:
            return None

        audio_bytes = b''.join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return audio_np

    def identify_speaker(self, audio_np):
        """
        Identifica o falante a partir do audio.
        Retorna: (is_user, similarity, label)
        """
        if not self.voiceprint.is_registered():
            return (True, 0.0, "sem_perfil")

        is_user, similarity, label = self.voiceprint.identify(audio_np)
        self._last_speaker = label
        self._last_similarity = similarity
        return (is_user, similarity, label)

    def get_last_speaker(self):
        """Retorna o ultimo falante identificado."""
        return self._last_speaker, self._last_similarity

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
        print("DEBUG AUDIO: Audio collector iniciado")
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
        print("DEBUG AUDIO: Audio processor iniciado")
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
        log_count = 0
        
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
                            log_count += 1
                            if log_count % 5 == 0:
                                print(f"DEBUG AUDIO: energy={energy:.4f}, window_len={len(self.wake_word_window)}")
                            if energy > 0.016:
                                from core.model_arbiter import arbiter
                                # Se o LLM é Cloud, o WHISPER pode ficar carregado permanentemente
                                arbiter.request_model("WHISPER")
                                
                                result = mlx_whisper.transcribe(
                                    audio_data, 
                                    path_or_hf_repo=self.whisper_model,
                                    language="pt",
                                    fp16=True # Mais rápido no M3
                                )
                                text = result["text"].lower().strip()
                                mx.clear_cache()
                                
                                if text:
                                    if log_count % 5 == 0:
                                        print(f"DEBUG WHISPER: '{text}'")
                                    words = text.split()
                                    if len(words) > 3 and len(set(words)) / len(words) < 0.4:
                                        last_process_time = time.time()
                                        continue

                                    if len(text) > 2 and "legendas" not in text:
                                        # Variações fonéticas de "Omni"
                                        omni_variants = ["omni", "omini", "homni", "ômine", "homeni", "homine", "amni", "omne", "ominy", "omyni", "hominy"]
                                        stop_keywords = ["chega", "parar", "silêncio", "stop", "quieto", "cala a boca"]
                                        # Lista negra de falsos positivos (foneticamente parecidos)
                                        falsepositives = ["menino", "harmonia", "dominó", "dominio", "comigo", "combinou", "iminal", "iminali"]
                                        
                                        text_clean = re.sub(r'[^\w\s]', '', text).lower()
                                        words_clean = text_clean.split()
                                        
                                        # Verificar se NÃO é falso positivo
                                        is_falsepositive = any(fp in text_clean for fp in falsepositives)
                                        
                                        # Wake word deve estar no INÍCIO (primeira palavra) para ativar
                                        is_omni = False
                                        if not is_falsepositive and words_clean:
                                            for kw in omni_variants:
                                                if words_clean[0] == kw:
                                                    is_omni = True
                                                    break
                                        
                                        # Stop keywords funcionam em qualquer lugar
                                        is_stop = any(re.search(r'\b' + re.escape(kw) + r'\b', text_clean) for kw in stop_keywords)

                                        if is_omni or is_stop:
                                            print(f"WAKE WORD/STOP DETECTADA: [{text}]")
                                            
                                            # BARGE-IN: Cala a boca imediatamente
                                            self.stop_speaking()
                                            
                                            # Verificar voiceprint ANTES do som de confirmação
                                            is_user = True  # Padrão: aceitar se não tiver voiceprint
                                            if self.voiceprint.is_registered():
                                                # Usar o áudio atual para identificação
                                                is_user, similarity, label = self.identify_speaker(audio_data)
                                                if not is_user:
                                                    print(f"Voiceprint: Voz desconhecida (sim={similarity:.2f}). Ignorando wake word.")
                                                    time.sleep(2.0)
                                                    continue
                                            
                                            # Tocar som de confirmação APENAS se for o usuário
                                            from core.sound_service import SoundService
                                            SoundService.beep()
                                            
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
                
                # Se so capturou a wake word isolada, ignora
                keywords = ["jarvis", "agente", "computador", "omni", "omniscient"]
                clean_verify = re.sub(r'[^\w\s]', '', final_text.lower()).strip()
                if clean_verify.split()[0] in keywords if clean_verify.split() else False:
                    return None
                    
                if len(final_text) < 2: return None

                # Descarta transcoes de ruido (caracteres repetidos excessivos)
                words = final_text.split()
                if words and len(words) > 3:
                    unique_ratio = len(set(w.lower() for w in words)) / len(words)
                    if unique_ratio < 0.2:
                        print(f"Voz: Transcricao descartada (ruido): {final_text[:50]}...")
                        self.is_listening_active = False
                        return None

                # Identificacao por voz (voiceprint)
                is_user, similarity, label = self.identify_speaker(audio_data)
                if not is_user and self.voiceprint.is_registered():
                    print(f"Voiceprint: Voz desconhecida (sim={similarity:.2f}). Comando ignorado.")
                    self.is_listening_active = False
                    return None

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
            with self.speaking_lock:
                if session_at_request != self.active_session_id: return

                try:
                    self.is_speaking = True
                    if self.status_callback: self.status_callback("SPEAKING", True)
                    
                    clean_text = re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
                    if "<think>" in clean_text.lower():
                        clean_text = clean_text.lower().split("<think>")[0]
                    
                    clean_text = re.sub(r'^(Pensamento|Raciocínio|Thought|Análise):.*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
                    clean_text = re.sub(r'[*#_`~]', '', clean_text)
                    clean_text = re.sub(r'\[.*?\]', '', clean_text).strip()
                    
                    if not clean_text or len(clean_text) < 2: return

                    cmd = ["say"]
                    cmd.append("--")
                    cmd.append(clean_text)
                    
                    self.current_playback_process = subprocess.Popen(cmd)
                    self.current_playback_process.wait()
                    self.current_playback_process = None
                except Exception as e:
                    print(f"ERRO VOZ NATIVO: {e}")
                finally:
                    self.is_speaking = False
                    if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()
