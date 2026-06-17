import mss
import mss.tools
from PIL import Image
import os
import threading


class VisionService:
    _instance = None
    _lock = threading.Lock()
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
        self.model_id = "mlx-community/Qwen2-VL-2B-Instruct-4bit"
        self._vision_enabled = os.getenv("VISION_ENABLED", "true").lower() in ("true", "1", "yes")
        self._model_loading = False
        status = "habilitada" if self._vision_enabled else "DESABILITADA (sem VISION_ENABLED)"
        print(f"Vision Service: Qwen2-VL ({status}).")
        self._initialized = True

    def preload(self):
        if not self._vision_enabled:
            return
        if self.model is not None:
            print("VisionService: Modelo já carregado.")
            return
        if self._model_loading:
            print("VisionService: Modelo já está sendo carregado.")
            return

        def _load():
            self._model_loading = True
            try:
                from mlx_vlm import load
                print(f"Pre-carregando {self.model_id} (Olhos do Agente)...")
                import mlx.core as mx
                with mx.stream(mx.default_stream(mx.gpu)):
                    self.model, self.processor = load(self.model_id)
                print("Visão Real pré-carregada (Qwen2-VL).")
            except Exception as e:
                print(f"Erro ao pré-carregar modelo de visão: {e}")
            finally:
                self._model_loading = False

        threading.Thread(target=_load, daemon=True).start()

    def _ensure_model_loaded(self):
        if not self._vision_enabled:
            print("VisionService: Visão DESABILITADA (VISION_ENABLED=false).")
            return

        import mlx.core as mx
        mx.set_default_stream(mx.default_stream(mx.gpu))

        if self.model is None and not self._model_loading:
            self._model_loading = True
            try:
                from mlx_vlm import load
                print(f"Carregando {self.model_id} (Olhos do Agente)...")
                self.model, self.processor = load(self.model_id)
                print("Visão Real ativada (Qwen2-VL).")
            except Exception as e:
                print(f"Erro ao carregar modelo de visão: {e}")
            finally:
                self._model_loading = False
        elif self._model_loading:
            while self._model_loading:
                import time
                time.sleep(0.1)

    @property
    def sct(self):
        if self._sct is None:
            try:
                self._sct = mss.MSS()
            except Exception as e:
                print(f"Erro ao inicializar mss: {e}")
                return None
        return self._sct

    def capture_screen_pil(self):
        sct = self.sct
        if sct is None: return None
        try:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            print(f"Erro na captura PIL: {e}")
            self._sct = None
            return None

    def describe_screen(self, prompt="O que você vê nesta tela? Descreva os aplicativos abertos e detalhes importantes."):
        if not self._vision_enabled:
            return "Visão desabilitada (VISION_ENABLED=false no .env)."

        import mlx.core as mx

        with VisionService._lock:
            mx.set_default_stream(mx.default_stream(mx.gpu))
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()
                if self.model is None:
                    return "Erro: Modelo de visão não carregado."

                img = self.capture_screen_pil()
                if img is None:
                    return "Não consegui capturar a tela."

                try:
                    from mlx_vlm import generate

                    img.thumbnail((1024, 1024))

                    result = generate(
                        model=self.model,
                        processor=self.processor,
                        image=img,
                        prompt=prompt,
                        max_tokens=80,
                        temperature=0.0
                    )

                    mx.clear_cache()

                    if hasattr(result, 'text'):
                        description = result.text
                    else:
                        description = str(result)
                    return description.strip()
                except Exception as e:
                    print(f"Erro na análise visual: {e}")
                    return f"Erro ao analisar a tela: {e}"