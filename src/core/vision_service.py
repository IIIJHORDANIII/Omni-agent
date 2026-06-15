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
    _lock = threading.Lock()

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
        print(f"Vision Service pronto para Apple Silicon (Qwen2-VL).")
        self._initialized = True

        from core.model_arbiter import arbiter
        arbiter.register_unloader("VISION", self.unload_model)

    def unload_model(self):
        """Libera o modelo da RAM/VRAM."""
        if self.model:
            print(f"VisionService: Descarregando {self.model_id} da RAM...")
            self.model = None
            self.processor = None
            # Força limpeza extra
            import gc
            import mlx.core as mx
            mx.clear_cache()
            gc.collect()

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        mx.set_default_stream(mx.default_stream(mx.gpu))

    def _ensure_model_loaded(self):
        """Carrega o modelo de visão apenas quando necessário."""
        from core.model_arbiter import arbiter
        if arbiter.request_model("VISION"):
            if self.model is None:
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
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()
                if self.model is None:
                    return "Erro: Modelo de visão não carregado."
                    
                img = self.capture_screen_pil()
                if img is None:
                    return "Não consegui capturar a tela."

                try:
                    img.thumbnail((1024, 1024))
                    
                    if self.model is None or self.processor is None:
                        return "Aguardando inicialização dos olhos (Qwen2-VL)..."

                    from mlx_vlm import generate as vlm_gen
                    
                    result = vlm_gen(
                        model=self.model, 
                        processor=self.processor, 
                        image=img, 
                        prompt=prompt, 
                        max_tokens=80
                    )
                    
                    mx.clear_cache()
                    
                    if isinstance(result, str):
                        description = result
                    elif hasattr(result, 'text'):
                        description = result.text
                    else:
                        description = str(result)
                        
                    return description.strip()
                except Exception as e:
                    print(f"Erro na análise visual (generate): {e}")
                    mx.clear_cache()
                    return f"Erro ao analisar a tela: {e}"

    def capture_webcam(self):
        """Captura uma foto da webcam usando o ffmpeg ou OpenCV como fallback."""
        import subprocess
        output = "/tmp/omni_face.jpg"
        
        # 1. Tenta via ffmpeg (mais rápido se as permissões estiverem ok)
        try:
            subprocess.run([
                "ffmpeg", "-y", "-f", "avfoundation", "-framerate", "30", "-i", "0", 
                "-frames:v", "1", "-update", "1", output
            ], capture_output=True, timeout=10)
            if os.path.exists(output):
                return Image.open(output)
        except: pass

        # 2. Fallback para OpenCV (cv2)
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return Image.fromarray(rgb_frame)
        except Exception as e:
            print(f"Erro ao acessar webcam (OpenCV): {e}")
        
        return None

    def recognize_user(self):
        """Tenta reconhecer se o usuario esta na frente da camera."""
        with VisionService._lock:
            self._ensure_stream()
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()

                # Busca o perfil visual na memoria
                memory = MemoryClient()
                profile = memory.get_fact("user_visual_profile", exact_only=True)

                if not profile or "Consultando" in profile or "Erro" in profile:
                    print("DEBUG VISION: Perfil visual nao encontrado. Executando registro automatico...")
                    reg_result = self.register_user()
                    if "sucesso" not in reg_result.lower():
                        print(f"DEBUG VISION: Falha no registro: {reg_result}")
                        return False
                    # Busca novamente apos registro
                    profile = memory.get_fact("user_visual_profile", exact_only=True)
                    if not profile:
                        return False

                img = self.capture_webcam()
                if img is None:
                    print("DEBUG VISION: Falha ao capturar webcam.")
                    return False

                if self.model is None or self.processor is None:
                    print("DEBUG VISION: Modelos de visao nao carregados.")
                    return False

                from mlx_vlm import generate as vlm_gen
                prompt = f"Analise esta imagem. A pessoa presente condiz com esta descricao fisica: '{profile}'? Responda apenas com SIM ou NAO."

                print("DEBUG VISION: Iniciando inferencia de reconhecimento...")
                result = vlm_gen(self.model, self.processor, image=img, prompt=prompt, max_tokens=10)

                mx.clear_cache()
                text = ""
                if isinstance(result, str): text = result.strip()
                elif hasattr(result, 'text'): text = result.text.strip()
                else: text = str(result).strip()

                print(f"DEBUG VISION: Resposta do modelo: '{text}'")
                # Match flexivel: SIM, Sim, sim, S, YES, Yes, yes, Y
                text_upper = text.upper().strip()
                return text_upper.startswith("SIM") or text_upper.startswith("YES") or text_upper == "S" or text_upper == "Y"

    def register_user(self):
        """Cria o perfil visual inicial do usuario."""
        with VisionService._lock:
            self._ensure_stream()
            with mx.stream(mx.default_stream(mx.gpu)):
                self._ensure_model_loaded()
                img = self.capture_webcam()
                if img is None: return "Nao consegui acessar a camera para o registro."

                if self.model is None or self.processor is None:
                    return "Hardware de visao indisponivel no momento."

                from mlx_vlm import generate as vlm_gen
                prompt = "Descreva detalhadamente as caracteristicas fisicas desta pessoa (cabelo, barba, oculos, tracos marcantes, roupa) para que eu posa reconhece-la depois. Seja muito preciso e objetivo."
                result = vlm_gen(self.model, self.processor, image=img, prompt=prompt, max_tokens=150)

                mx.clear_cache()
                profile = ""
                if isinstance(result, str): profile = result
                elif hasattr(result, 'text'): profile = result.text
                else: profile = str(result)

                if profile and len(profile) > 10:
                    memory = MemoryClient()
                    memory.save_fact("user_visual_profile", profile)
                    return f"Perfil visual criado com sucesso: {profile[:100]}..."
                return "Falha ao gerar perfil visual."
