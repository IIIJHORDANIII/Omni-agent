import mss
import mss.tools
from PIL import Image
import io
import base64
import os
import mlx.core as mx
import threading
from mlx_vlm import load, generate
from mlx_vlm.utils import load_config
from core.memory_client import MemoryClient

class VisionService:
    _instance = None
    _lock = threading.Lock() # Lock de classe para evitar concorrência no Metal/RAM
    _thread_local = threading.local()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VisionService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        self._sct = None
        self.model = None
        self.processor = None
        self.config = None
        # Qwen2-VL 2B: Ultra-leve (1.5GB), preciso e rápido
        self.model_id = "mlx-community/Qwen2-VL-2B-Instruct-4bit" 
        print(f"Vision Service pronto para Apple Silicon (Qwen2-VL).")
        self._initialized = True

        # Registro no Arbiter para permitir descarga real da RAM
        from core.model_arbiter import arbiter
        arbiter.register_unloader("VISION", self.unload_model)

    def unload_model(self):
        """Libera o modelo da RAM/VRAM."""
        if self.model:
            print(f"VisionService: Descarregando {self.model_id} da RAM...")
            self.model = None
            self.processor = None

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        mx.set_default_stream(mx.default_stream(mx.gpu))

    def _ensure_model_loaded(self):
        """Carrega o modelo de visão apenas quando necessário (lazy load)."""
        from core.model_arbiter import arbiter
        if arbiter.request_model("VISION"):
            if self.model is None:
                print(f"Carregando {self.model_id} (Olhos do Agente)...")
                try:
                    self.model, self.processor = load(self.model_id)
                    print("Visão Real ativada (Qwen2-VL).")
                except Exception as e:
                    print(f"Erro ao carregar modelo de visão: {e}")

    @property
    def sct(self):
        if self._sct is None:
            try:
                self._sct = mss.mss()
            except Exception as e:
                print(f"Erro ao inicializar mss: {e}")
                return None
        return self._sct

    def capture_screen_pil(self):
        """Captura a tela principal."""
        sct = self.sct
        if sct is None: return None
        try:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            print(f"Erro na captura PIL: {e}")
            # Se der erro de FD, reseta o mss para a próxima tentativa
            self._sct = None
            return None

    def describe_screen(self, prompt="O que você vê nesta tela? Descreva os aplicativos abertos e detalhes importantes."):
        """Usa Qwen2-VL para descrever a imagem da tela com proteção de memória."""
        with VisionService._lock:
            self._ensure_stream()
            # FIX: Garante que cada thread tenha seu stream GPU inicializado e bound via context manager
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()
                if self.model is None:
                    return "Erro: Modelo de visão não carregado."
                    
                img = self.capture_screen_pil()
                if img is None:
                    return "Não consegui capturar a tela."

                try:
                    # Otimiza imagem para o Qwen2-VL
                    img.thumbnail((1024, 1024))
                    
                    # MLX-VLM Inference
                    result = generate(
                        model=self.model, 
                        processor=self.processor, 
                        image=img, 
                        prompt=prompt, 
                        max_tokens=80,
                        temperature=0.0
                    )
                    
                    # Limpa cache do Metal após processamento de imagem
                    mx.clear_cache()
                    
                    # Converte o objeto de resultado para string (pega o texto gerado)
                    if hasattr(result, 'text'):
                        description = result.text
                    else:
                        description = str(result)
                    return description.strip()
                except Exception as e:
                    print(f"Erro na análise visual: {e}")
                    return f"Erro ao analisar a tela: {e}"

    def capture_webcam(self):
        """Captura uma foto da webcam usando o ffmpeg (mais leve para macOS)."""
        import subprocess
        output = "/tmp/omni_face.jpg"
        try:
            # Captura 1 frame da webcam padrão
            subprocess.run([
                "ffmpeg", "-y", "-f", "avfoundation", "-video_size", "640x480", 
                "-i", "0", "-frames:v", "1", output
            ], capture_output=True, timeout=5)
            if os.path.exists(output):
                return Image.open(output)
        except Exception as e:
            print(f"Erro ao acessar webcam: {e}")
        return None

    def recognize_user(self):
        """Tenta reconhecer se o Jhordan está na frente da câmera."""
        with VisionService._lock:
            self._ensure_stream()
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()
                
                # Busca o perfil visual na memória
                memory = MemoryClient()
                profile = memory.get_fact("visual_profile_jhordan")
                if not profile:
                    return False # Sem perfil, sem reconhecimento
                
                img = self.capture_webcam()
                if img is None: return False
                
                prompt = f"A pessoa nesta imagem condiz com esta descrição: '{profile}'? Responda apenas SIM ou NAO."
                result = generate(self.model, self.processor, image=img, prompt=prompt, max_tokens=10)
                text = result.text.upper() if hasattr(result, 'text') else str(result).upper()
                
                return "SIM" in text or "YES" in text

    def register_user(self):
        """Cria o perfil visual inicial do Jhordan."""
        with VisionService._lock:
            self._ensure_stream()
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()
                img = self.capture_webcam()
                if img is None: return "Não consegui acessar a câmera para o registro."
                
                prompt = "Descreva detalhadamente as características físicas desta pessoa (cabelo, barba, óculos, traços marcantes) para que eu possa reconhecê-la depois. Seja muito preciso."
                result = generate(self.model, self.processor, image=img, prompt=prompt, max_tokens=150)
                profile = result.text if hasattr(result, 'text') else str(result)
                
                if profile:
                    memory = MemoryClient()
                    memory.save_fact("visual_profile_jhordan", profile)
                    return f"Perfil visual criado com sucesso: {profile[:100]}..."
                return "Falha ao gerar perfil visual."
