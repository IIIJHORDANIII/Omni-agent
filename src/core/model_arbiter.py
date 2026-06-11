import threading
import mlx.core as mx
import gc

class ModelArbiter:
    """
    Coordena o carregamento e descarregamento de modelos pesados no Metal.
    Evita que Whisper, Vision e LLM colidam em memória.
    """
    _instance = None
    _lock = threading.Lock()
    _active_model = None # "WHISPER", "VISION", "LLM"

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelArbiter, cls).__new__(cls)
            return cls._instance

    def request_model(self, model_type):
        """Solicita permissão para usar um modelo, descarregando outros se necessário."""
        with self._lock:
            if self._active_model == model_type:
                return True

            print(f"Arbiter: Solicitando {model_type}. Descarregando {self._active_model}...")
            self._unload_all()
            self._active_model = model_type
            return True

    def _unload_all(self):
        """Limpa cache do MLX e chama o coletor de lixo."""
        try:
            mx.clear_cache()
            gc.collect()
        except Exception as e:
            print(f"Arbiter: Erro ao limpar memória: {e}")

    def release_all(self):
        with self._lock:
            self._unload_all()
            self._active_model = None

# Instância global
arbiter = ModelArbiter()
