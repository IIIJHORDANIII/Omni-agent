import threading
import os
import httpx
import json
import re
from mlx_lm import load, generate
import mlx.core as mx
from core.context_service import ContextService

class LLMManager:
    _instance = None
    _thread_local = threading.local()
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LLMManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path="mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"):
        if self._initialized: return
        self.refresh_config()
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self._initialized = True
        from core.model_arbiter import arbiter
        arbiter.register_unloader("LLM", self.unload_model)

    def refresh_config(self):
        """Recarrega as configuracoes do .env para respeitar mudancas no setup."""
        from dotenv import load_dotenv
        load_dotenv(override=True)
        self.provider = os.getenv("LLM_PROVIDER", "LOCAL").upper()
        self.model_name = os.getenv("LLM_MODEL", "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit")
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"

        # Configuracoes para outros provedores
        if self.provider == "ANTHROPIC":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        elif self.provider == "GOOGLE":
            self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")

        print(f"Cerebro Raciocinante atualizado (Provider: {self.provider}).")

    def unload_model(self):
        if self.model:
            print(f"LLMManager: Descarregando modelo da RAM...")
            self.model = None
            self.tokenizer = None

    def _ensure_model_loaded(self):
        if self.provider != "LOCAL" and self.provider != "MLX": return
        from core.model_arbiter import arbiter
        if arbiter.request_model("LLM"):
            if self.model is None:
                print(f"Carregando {self.model_path} no Metal...")
                self.model, self.tokenizer = load(self.model_path)

    def _ensure_stream(self):
        if self.provider == "LOCAL" or self.provider == "MLX":
            mx.set_default_stream(mx.default_stream(mx.gpu))

    def generate_command(self, prompt_or_messages, system_context=""):
        # Garante que o provedor esteja atualizado antes de cada comando critico
        if not hasattr(self, 'provider') or self.provider == "LOCAL":
             self.refresh_config()

        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            current_ctx = ContextService.get_context_str()
            system_prompt = f"Voce e o OMNISCIENT. Responda em PT-BR. Seja EXTREMAMENTE conciso: maximo 1-2 frases. Nao explique o obvio. Va direto ao ponto.\n{current_ctx}"
            if system_context: system_prompt += f"\nCONTEXTO: {system_context}"
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt_or_messages}]

        print(f"DEBUG LLM: Provider={self.provider}, has_key={bool(self.api_key)}, msgs={len(messages)}")
        
        # Roteamento por provedor
        if self.provider == "DEEPSEEK" and self.api_key:
            return self._generate_deepseek(messages)
        elif self.provider == "ANTHROPIC" and self.api_key:
            return self._generate_anthropic(messages)
        elif self.provider == "GOOGLE" and self.api_key:
            return self._generate_google(messages)
        else:
            return self._generate_mlx(messages, system_context)

    def _generate_deepseek(self, messages):
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7}
            print(f"DEBUG DEEPSEEK: Enviando {len(messages)} mensagens...")
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                print(f"DEBUG DEEPSEEK: Status {response.status_code}")
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                print(f"DEBUG DEEPSEEK: Resposta: '{content[:100]}'")
                return self._post_process(content)
        except Exception as e:
            print(f"ERRO CLOUD (DeepSeek): {e}")
            return f"Erro DeepSeek Cloud: {e}"

    def _generate_anthropic(self, messages):
        try:
            # Anthropic API: system vai separado
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": self.model_name,
                "max_tokens": 1000,
                "messages": user_messages
            }
            if system_msg:
                payload["system"] = system_msg

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers, json=payload
                )
                response.raise_for_status()
                result = response.json()
                return self._post_process(result["content"][0]["text"])
        except Exception as e:
            print(f"ERRO CLOUD (Anthropic): {e}")
            return f"Erro Anthropic Cloud: {e}"

    def _generate_google(self, messages):
        try:
            # Google Gemini API
            contents = []
            for msg in messages:
                role = msg["role"] if msg["role"] in ("user", "model") else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

            model = self.model_name or "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

            payload = {"contents": contents}
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return self._post_process(text)
        except Exception as e:
            print(f"ERRO CLOUD (Google): {e}")
            return f"Erro Google Cloud: {e}"

    def _generate_mlx(self, messages, system_context=""):
        self._ensure_stream()
        with self._lock:
            try:
                self._ensure_model_loaded()
                if self.model is None: return "Erro: Modelo local não carregado."
                prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                
                from mlx_lm import generate as mlx_gen
                response = mlx_gen(
                    self.model, 
                    self.tokenizer, 
                    prompt=prompt, 
                    max_tokens=1000,
                    verbose=False
                )
                mx.clear_cache()
                return self._post_process(response)
            except Exception as e:
                print(f"ERRO MLX LOCAL: {e}")
                return f"Erro na geração local: {e}"

    def _post_process(self, response):
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        if "</think>" in response: response = response.split("</think>")[-1]
        return response.replace("<think>", "").strip()
