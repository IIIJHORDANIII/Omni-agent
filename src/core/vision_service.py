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

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        mx.set_default_stream(mx.default_stream(mx.gpu))

    def _ensure_model_loaded(self):
        """Carrega o modelo de visão apenas quando necessário."""
        if self.model is None:
            import gc
            gc.collect()
            try:
                mx.clear_cache()
            except: pass
            
            print(f"Carregando {self.model_id} (Olhos do Agente)...")
            try:
                # Carrega o modelo de visão multimodal
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

    def capture_screen_base64(self):
        """Legado: Captura a tela e converte para base64."""
        img = self.capture_screen_pil()
        if img is None: return ""
        try:
            buffered = io.BytesIO()
            img.thumbnail((512, 512)) 
            img.save(buffered, format="JPEG", quality=60)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
