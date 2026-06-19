import threading
import os
import subprocess
import numpy as np
import re
import time
from queue import Queue
import io
import wave

from core.deepgram_transcriber import transcribe_wav_bytes
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

    def __init__(self, on_wake_word_detected=None, use_remote=False):
        with VoiceService._lock:
            if getattr(self, '_initialized', False):
                return
        self.use_remote = use_remote
        self._is_speaking_internal = False
        self.on_wake_word_detected = on_wake_word_detected
        self.status_callback = None
        self.amplitude_callback = None
        self.running = True
        self.audio_lock = threading.Lock()
        self.speaking_lock = threading.Lock()

        # Attempt to import pyaudio; if unavailable, use a dummy stub
        try:
            import pyaudio
            self.FORMAT = pyaudio.paInt16
            self.p = pyaudio.PyAudio()
        except Exception as e:
            print(f"Warning: pyaudio not available ({e}); using dummy audio stub.")
            class DummyStream:
                def __init__(self):
                    pass
                def read(self, chunk_size, **kwargs):
                    # Retorna 2 bytes por sample de zeros para evitar falha no calculo de energia/amplitude
                    return b"\x00" * (chunk_size * 2)
                def stop_stream(self):
                    pass
                def close(self):
                    pass
            class DummyPyAudio:
                paInt16 = None
                def open(self, *args, **kwargs):
                    return DummyStream()
                def terminate(self):
                    pass
            self.FORMAT = None
            self.p = DummyPyAudio()
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        
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



        self.wake_word_window = []
        self.window_seconds = 4.0
        self.samples_needed = int(self.RATE * self.window_seconds)
        self.is_continuous_mode = False
        self._last_speak_end_time = 0.0
        self._last_spoken_text = ""
        self._initialized = True

    def toggle_continuous_mode(self, enabled=None):
        if enabled is None:
            self.is_continuous_mode = not self.is_continuous_mode
        else:
            self.is_continuous_mode = enabled
        print(f"Voz: Modo Contínuo {'ATIVADO' if self.is_continuous_mode else 'DESATIVADO'}")
        return self.is_continuous_mode

    @property
    def is_speaking(self):
        if hasattr(self, 'piper') and self.use_piper:
            return self.piper.is_speaking
        if hasattr(self, 'kokoro') and self.use_kokoro:
            return self.kokoro.is_speaking
        return getattr(self, "_is_speaking_internal", False)

    @is_speaking.setter
    def is_speaking(self, value):
        self._is_speaking_internal = value

    def _ensure_stream(self):
        """Placeholder for compatibility; no MLX stream needed."""
        pass





    def _audio_to_wav_bytes(self, audio_np: "numpy.ndarray") -> bytes:
        """Convert a float32 PCM numpy array (range -1..1) to WAV bytes.
        The resulting bytes can be sent directly to Deepgram.
        """
        # Ensure correct shape
        if audio_np.ndim != 1:
            audio_np = audio_np.flatten()
        int16_data = (audio_np * 32767).astype("int16")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.RATE)
            wf.writeframes(int16_data.tobytes())
        return buf.getvalue()

    def start_listening_mode(self):
        if not hasattr(self, 'threads_started'):
            threading.Thread(target=self._audio_collector, daemon=True).start()
            threading.Thread(target=self._audio_processor, daemon=True).start()
            threading.Thread(target=self._global_audio_watchdog, daemon=True).start()

            self.threads_started = True

    def clear_buffers(self):
        """Limpa todos os buffers de áudio para evitar gatilhos fantasmas de áudio antigo."""
        with self.audio_lock:
            self.wake_word_window = []
        while not self.audio_buffer.empty():
            try:
                self.audio_buffer.get_nowait()
            except:
                break
        print("Voz: Buffers de áudio limpos.")

    def start_wake_word_detection(self, callback=None):
        if callback:
            self.on_wake_word_detected = callback

        self.start_listening_mode()
        # Limpa os buffers ANTES de começar o loop para não ouvir a própria saudação/ruído de boot
        self.clear_buffers()
        threading.Thread(target=self._run_wake_word_loop, daemon=True).start()

    def _global_audio_watchdog(self):
        while self.running:
            if time.time() - self.last_audio_time > 10.0:
                self._reset_stream()
                self.last_audio_time = time.time()
            time.sleep(5)

    def _audio_collector(self):
        while self.running:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)

                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                energy = np.sqrt(np.mean(audio_np**2))
                
                # O buffer de áudio (Wake Word e Escuta) deve ser SEMPRE alimentado.
                # Removemos qualquer threshold aqui para garantir que o Whisper receba 100% do sinal.
                self.audio_buffer.put(data)

                # O Noise Gate deve ser aplicado APENAS visualmente no HUD
                is_visual_noise = energy < 0.005 

                if self.amplitude_callback:
                    try:
                        self.amplitude_callback(0 if is_visual_noise else energy)
                    except Exception:
                        pass
                
                if self.spectrum_callback:
                    try:
                        if is_visual_noise:
                            # HUD fica quieto se for apenas ruído de fundo
                            self.spectrum_callback([0.0] * 20)
                        else:
                            # FFT para o espectro visual
                            fft_res = np.abs(np.fft.rfft(audio_np))
                            bins = 20
                            chunk_per_bin = len(fft_res) // bins
                            if chunk_per_bin > 0:
                                spectrum = [float(np.mean(fft_res[i*chunk_per_bin : (i+1)*chunk_per_bin])) for i in range(bins)]
                                self.spectrum_callback(spectrum)
                    except Exception:
                        pass

                self.last_audio_time = time.time()
            except Exception as e:
                print(f"Erro na coleta de áudio: {e}")
                self._reset_stream()
                time.sleep(0.5)

    def _audio_processor(self):
        while self.running:
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

        print("Monitorando Wake Word (Deepgram remote)...")
        last_process_time = time.time()

        while self.running:
            if time.time() - last_process_time > 1.2:
                if self.is_speaking:
                    last_process_time = time.time()
                    continue
                time_since_spoke = time.time() - getattr(self, '_last_speak_end_time', 0)
                if time_since_spoke < 0.5:
                    last_process_time = time.time()
                    continue

                audio_data = None
                with self.audio_lock:
                    if len(self.wake_word_window) >= self.RATE:
                        audio_data = np.array(self.wake_word_window, dtype=np.float32)

                if audio_data is not None:
                    # Remote transcription only
                    try:
                        energy = np.sqrt(np.mean(audio_data**2))
                        if energy > 0.015:
                            if self.use_remote:
                                wav_bytes = self._audio_to_wav_bytes(audio_data)
                                text = transcribe_wav_bytes(wav_bytes, language="pt-BR")
                            else:
                                # Local Whisper not available; skip processing
                                continue

                            if text:
                                # Existing wake word detection logic (retain)
                                words = text.split()
                                if len(words) > 3 and len(set(words)) / len(words) < 0.3:
                                    last_process_time = time.time()
                                    continue

                                # Suppress echo logic (unchanged)
                                anders_variants = ["anders", "enders", "andres", "andrews", "handers", "amders", "agent", "an", "anda", "and"]
                                words_in_text = re.sub(r'[^\w\s]', '', text).split()
                                is_wake_candidate = any(kw in words_in_text for kw in anders_variants)

                                if self._last_spoken_text and not is_wake_candidate:
                                    spoken_words = set(re.sub(r'[^\w\s]', '', self._last_spoken_text.lower()).split())
                                    text_words = set(re.sub(r'[^\w\s]', '', text).split())
                                    overlap = spoken_words & text_words
                                    if len(overlap) >= 2 and (len(overlap) / max(len(text_words), 1) > 0.5):
                                        print(f"ECO SUPRIMIDO: texto '{text}' parece eco da fala do agente.")
                                        last_process_time = time.time()
                                        continue

                                if len(text) > 2 and "legendas" not in text:
                                    stop_keywords = ["chega", "silêncio", "stop", "quieto", "cala a boca"]
                                    words_in_text = re.sub(r'[^\w\s]', '', text).split()
                                    is_wake = any(kw in words_in_text for kw in anders_variants)
                                    is_stop = any(kw in words_in_text for kw in stop_keywords)
                                    if is_wake or is_stop:
                                        print(f"WAKE WORD/STOP DETECTADA: [{text}]")
                                        self.stop_speaking()
                                        if is_wake:
                                            # Speaker verification retained
                                            try:
                                                from core.speaker_verification import speaker_verifier
                                                if speaker_verifier.load_reference():
                                                    with self.audio_lock:
                                                        verify_audio = np.array(self.wake_word_window, dtype=np.float32)
                                                    print(f"SpeakerVerifier: Verificando {len(verify_audio)} amostras de áudio...")
                                                    is_owner = speaker_verifier.verify(verify_audio, return_score=True)
                                                    print(f"SpeakerVerifier: Resultado={is_owner}")
                                                    if not is_owner[0]:
                                                        print(f"SpeakerVerifier: Wake word detectada mas voz NÃO reconhecida (score={is_owner[1]:.3f}). Ignorando.")
                                                        last_process_time = time.time()
                                                        continue
                                                    print(f"SpeakerVerifier: Voz reconhecida! (score={is_owner[1]:.3f})")
                                            except Exception as e:
                                                print(f"SpeakerVerifier: Erro na verificação (permitindo): {e}")
                                        # Clear buffers
                                        with self.audio_lock:
                                            self.wake_word_window = []
                                        while not self.audio_buffer.empty():
                                            try:
                                                self.audio_buffer.get_nowait()
                                            except:
                                                break
                                        if self.on_wake_word_detected:
                                            self.on_wake_word_detected()
                                        time.sleep(1.5)
                    except Exception as e:
                        print(f"Erro na transcrição Wake Word: {e}")
                last_process_time = time.time()
            time.sleep(0.1)

    def listen(self, continuous_mode=False, timeout=None):

        print(f"Ouvindo comando... {'(timeout: ' + str(timeout) + 's)' if timeout else ''}")
        self.is_listening_active = True
        self.abort_listen = False
        start_time = time.time()
        recorded_audio = []
        silence_start = None

        # --- NOVA LÓGICA DE DETECÇÃO DE FALA (VAD SIMPLES) ---
        energy_threshold = 0.040  # Increased from 0.015 to prevent background noise triggers
        
        # max_duration é o limite total de segurança (evita gravar pra sempre)
        max_duration = 15 
        
        # Se houver timeout, ele serve como o 'grace period' (tempo para COMEÇAR a falar)
        initial_wait = timeout if timeout else 4.0
        
        silence_pad = [0.0] * int(self.RATE * 0.1)

        with self.audio_lock:
            if not continuous_mode and self.wake_word_window:
                recorded_audio.extend(self.wake_word_window)

            while not self.audio_buffer.empty():
                try:
                    self.audio_buffer.get_nowait()
                except:
                    break
            self.wake_word_window = []

        speech_detected = False
        while time.time() - start_time < max_duration:
            if self.abort_listen:
                print("Escuta interrompida por nova Wake Word.")
                return None

            while not self.audio_buffer.empty():
                chunk = self.audio_buffer.get()
                audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                energy = np.sqrt(np.mean(audio_np**2))

                # Se detectou som acima do threshold, marca que a fala começou
                if energy > energy_threshold:
                    if not speech_detected:
                        print("🎙️ Som detectado! Pode falar...")
                    speech_detected = True
                    silence_start = None
                elif speech_detected and silence_start is None:
                    silence_start = time.time()

                # SEMPRE adiciona o áudio, para não "picotar" a voz e destruir o áudio
                recorded_audio.extend(audio_np.tolist())

            elapsed = time.time() - start_time
            
            # LÓGICA DINÂMICA:
            # 1. Se ainda não detectou fala e o tempo inicial acabou -> Sai
            if not speech_detected and elapsed > initial_wait:
                print(f"Escuta: Nenhuma fala detectada em {initial_wait}s.")
                self.is_listening_active = False
                return None
            
            # 2. Se detectou fala e ficou em silêncio por 1.5s -> Processa (Increased from 1.2s to give more time to speak)
            if speech_detected and silence_start and (time.time() - silence_start > 1.5):
                break
                
            time.sleep(0.01)

        if self.abort_listen:
            self.is_listening_active = False
            return None

        recorded_audio.extend(silence_pad)

        if not recorded_audio or len(recorded_audio) < self.RATE * 0.5:
            print(f"Escuta: Áudio muito curto ({len(recorded_audio)} amostras).")
            self.is_listening_active = False
            return None

        print("Sintonizando voz...")
        self._ensure_stream()
        # Remote transcription only; no local Whisper.
        try:
            wav_bytes = self._audio_to_wav_bytes(np.array(recorded_audio, dtype=np.float32))
            final_text = transcribe_wav_bytes(wav_bytes, language="pt-BR")
            
            # Print explícito do que o Deepgram ouviu
            if not final_text:
                print("❌ Nenhuma fala reconhecida pelo Deepgram (texto vazio).")
            else:
                print(f"🎙️ O que o Deepgram ouviu: '{final_text}' (Energia Máxima: {np.max(np.abs(np.array(recorded_audio)))})")
            
            wake_word_variants = ["anders", "enders", "andres", "andrews", "handers", "amders", "agent", "computador", "que louco", "oi", "hã", "hein", "hm", "ah"]
            clean_verify = re.sub(r'[^\w\s]', '', final_text.lower()).strip()
            if len(final_text) < 2:
                self.is_listening_active = False
                return None

            # Alucinação filter
            words = final_text.lower().split()
            if len(words) > 10:
                from collections import Counter
                counts = Counter(words)
                most_common_word, count = counts.most_common(1)[0]
                if count / len(words) > 0.5:
                    print(f"Alucinação detectada e filtrada: [{most_common_word}] repetido {count} vezes.")
                    self.is_speaking = False
                    self.is_listening_active = False
                    return None

            print(f"Comando completo: {final_text}")
            self.is_speaking = False
            return final_text
        except Exception as e:
            print(f"Erro na transcrição: {e}")
            self.is_listening_active = False
            return None

    def stop_speaking(self):
        self.active_session_id += 1
        self.abort_listen = True

        if hasattr(self, 'piper'):
            self.piper.stop_speaking()

        if hasattr(self, 'kokoro'):
            self.kokoro.stop_speaking()

        try:
            subprocess.run(["killall", "say"], capture_output=True)
        except:
            pass
        self.current_playback_process = None
        self.is_speaking = False
        self._last_speak_end_time = time.time()

    def speak(self, text):
        if not text: return

        self.is_speaking = True
        session_at_request = self.active_session_id

        self._last_spoken_text = text

        with self.audio_lock:
            self.wake_word_window = []

        self._speak_native(text, session_at_request)

    def _speak_native(self, text, session_at_request):
        from utils.tts_preprocessor import preprocess_for_tts

        def _speak():
            with self.speaking_lock:
                if session_at_request != self.active_session_id: return

                try:
                    self.is_speaking = True
                    if self.status_callback: self.status_callback("SPEAKING", True)

                    clean_text = re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
                    think_close = "</" + "think>"
                    if think_close in clean_text:
                        parts = clean_text.split(think_close)
                        clean_text = parts[-1] if parts else clean_text
                    think_open = "<" + "think>"
                    clean_text = clean_text.replace(think_open, "")

                    clean_text = re.sub(r'^(Pensamento|Raciocinio|Thought|Analise):.*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)

                    clean_text = preprocess_for_tts(clean_text)

                    clean_text = preprocess_for_tts(clean_text)

                    if not clean_text or len(clean_text) < 2: return

                    print(f"FALANDO (Voz Padrão do Sistema): {clean_text}")
                    self.current_playback_process = subprocess.Popen(["say", "--", clean_text])
                    self.current_playback_process.wait()
                    self.current_playback_process = None
                except Exception as e:
                    print(f"ERRO VOZ NATIVO: {e}")
                finally:
                    self.is_speaking = False
                    if self.status_callback: self.status_callback("SPEAKING", False)

        threading.Thread(target=_speak, daemon=True).start()