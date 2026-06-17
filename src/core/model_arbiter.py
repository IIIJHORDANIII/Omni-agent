import threading
import gc
import os


class ModelArbiter:
    _instance = None
    _lock = threading.Lock()
    _active_model = None
    _unloaders = {}
    _cloud_mode = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelArbiter, cls).__new__(cls)
            return cls._instance

    def _is_cloud(self):
        if self._cloud_mode is not None:
            return self._cloud_mode
        provider = os.getenv("LLM_PROVIDER", "").upper()
        if provider == "LOCAL" or provider == "MLX":
            self._cloud_mode = False
            return False
        if os.getenv("DEEPSEEK_API_KEY", "").strip() or \
           os.getenv("ANTHROPIC_API_KEY", "").strip() or \
           os.getenv("GOOGLE_GENERATIVE_AI_API_KEY", "").strip():
            self._cloud_mode = True
            return True
        self._cloud_mode = False
        return False

    def register_unloader(self, model_type, callback):
        self._unloaders[model_type] = callback

    def request_model(self, model_type):
        if self._is_cloud():
            print(f"Arbiter: Modo Cloud ativo. {model_type} compartilha GPU sem restrições.")
            return True

        with self._lock:
            if self._active_model == model_type:
                return True

            print(f"Arbiter: Solicitando {model_type}. Liberando {self._active_model}...")

            if self._active_model in self._unloaders:
                try:
                    self._unloaders[self._active_model]()
                except Exception as e:
                    print(f"Arbiter: Erro ao descarregar {self._active_model}: {e}")

            self._unload_all()
            self._active_model = model_type
            return True

    def _unload_all(self):
        try:
            import mlx.core as mx
            mx.clear_cache()
            gc.collect()
        except ImportError:
            gc.collect()
        except Exception as e:
            print(f"Arbiter: Erro ao limpar memória: {e}")

    def release_all(self):
        with self._lock:
            self._unload_all()
            self._active_model = None


arbiter = ModelArbiter()