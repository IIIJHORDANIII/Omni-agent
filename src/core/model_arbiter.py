import threading
import mlx.core as mx
import gc
import os

class ModelArbiter:
    """
    Coordena o carregamento e descarregamento de modelos pesados no Metal.
    Prioriza a permanência do Whisper se o LLM for Cloud.
    """
    _instance = None
    _lock = threading.Lock()
    _active_model = None # "WHISPER", "VISION", "LLM"
    _unloaders = {} # model_type -> callback

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelArbiter, cls).__new__(cls)
            return cls._instance

    def register_unloader(self, model_type, callback):
        self._unloaders[model_type] = callback

    def request_model(self, model_type):
        """Solicita um modelo, otimizando o uso do Metal."""
        import time
        with self._lock:
            if self._active_model == model_type:
                return True

            # Se o usuário usa DeepSeek Cloud, não precisamos descarregar o Whisper 
            # para dar espaço ao LLM (pois o LLM não usa a placa de vídeo local).
            is_cloud = os.getenv("LLM_PROVIDER", "LOCAL").upper() == "DEEPSEEK"
            
            if model_type == "LLM" and is_cloud:
                # No modo Cloud, o LLM e o Whisper podem coexistir
                return True

            print(f"Arbiter: Solicitando {model_type}. Liberando {self._active_model}...")
            
            # Unload o modelo anterior se não for possível coexistir
            if self._active_model in self._unloaders:
                try:
                    self._unloaders[self._active_model]()
                except Exception as e:
                    print(f"Arbiter: Erro unloader {self._active_model}: {e}")

            self._unload_all()
            time.sleep(0.3) # Respiro para o Metal
            
            self._active_model = model_type
            return True

    def _unload_all(self):
        try:
            mx.clear_cache()
            gc.collect()
        except Exception as e:
            print(f"Arbiter: Erro limpeza: {e}")

    def release_all(self):
        with self._lock:
            self._unload_all()
            self._active_model = None

# Instância global
arbiter = ModelArbiter()
