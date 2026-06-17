import threading
import os
import re
import httpx
import json
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

    @staticmethod
    def _detect_provider():
        explicit = os.getenv("LLM_PROVIDER", "").upper()
        if explicit in ("DEEPSEEK", "ANTHROPIC", "GOOGLE", "LOCAL", "MLX"):
            return explicit

        if os.getenv("DEEPSEEK_API_KEY", "").strip():
            return "DEEPSEEK"
        if os.getenv("ANTHROPIC_API_KEY", "").strip():
            return "ANTHROPIC"
        if os.getenv("GOOGLE_GENERATIVE_AI_API_KEY", "").strip():
            return "GOOGLE"

        return "LOCAL"

    def __init__(self, model_path="mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"):
        if self._initialized: return
        self.provider = self._detect_provider()
        self.model_name = os.getenv("LLM_MODEL", model_path)
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"

        self.model_path = model_path
        self.model = None
        self.tokenizer = None

        print(f"LLMManager: Provider detectado = {self.provider} (auto-detecção baseada em chaves de API)")
        self._initialized = True

        from core.model_arbiter import arbiter
        arbiter.register_unloader("LLM", self.unload_model)

    def unload_model(self):
        if self.model:
            print(f"LLMManager: Descarregando {self.model_path} da RAM...")
            self.model = None
            self.tokenizer = None

    def _ensure_model_loaded(self):
        if self.provider not in ("LOCAL", "MLX"):
            return

        import mlx.core as mx
        from mlx_lm import load, generate

        from core.model_arbiter import arbiter
        if arbiter.request_model("LLM"):
            if self.model is None:
                print(f"Carregando {self.model_path} no Metal...")
                self.model, self.tokenizer = load(self.model_path)
                print("Cérebro DeepSeek-R1 pronto (Local).")

    def _ensure_stream(self):
        if self.provider in ("LOCAL", "MLX"):
            import mlx.core as mx
            mx.set_default_stream(mx.default_stream(mx.gpu))

    def generate_command(self, prompt_or_messages, system_context=""):
        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            current_ctx = ContextService.get_context_str()
            system_prompt = f"Você é o ANDERS, assistente para macOS. Responda em PT-BR de forma concisa. Termos técnicos em inglês (API, JSON, URL, etc.) mantenha em inglês — NÃO traduza siglas nem jargões de programação.\n{current_ctx}"
            if system_context:
                system_prompt += f"\nCONTEXTO ADICIONAL: {system_context}"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_or_messages}
            ]

        if self.provider == "DEEPSEEK":
            return self._generate_deepseek(messages, system_context)
        elif self.provider == "ANTHROPIC":
            return self._generate_anthropic(messages, system_context)
        elif self.provider == "GOOGLE":
            return self._generate_google(messages, system_context)
        else:
            return self._generate_mlx(messages, system_context)

    def _generate_mlx(self, messages, system_context=""):
        from mlx_lm import generate

        self._ensure_stream()
        with self._lock:
            try:
                self._ensure_model_loaded()
                if self.model is None:
                    return "Erro: Modelo local não carregado."

                full_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                response = generate(self.model, self.tokenizer, prompt=full_prompt, max_tokens=600)

                if hasattr(response, 'text'):
                    result = response.text
                else:
                    result = str(response)

                return self._post_process(result, messages, system_context)
            except Exception as e:
                print(f"ERRO MLX: {e}")
                return f"Erro na geração local: {e}"

    def _generate_deepseek(self, messages, system_context=""):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                return self._post_process(content, messages, system_context)
        except Exception as e:
            print(f"ERRO DEEPSEEK CLOUD: {e}")
            return f"Erro ao acessar DeepSeek Cloud: {e}"

    def _generate_anthropic(self, messages, system_context=""):
        try:
            import google.generativeai as genai

            headers = {
                "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            system_msg = ""
            chat_msgs = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    chat_msgs.append(m)

            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": system_msg,
                "messages": chat_msgs
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["content"][0]["text"]
                return self._post_process(content, messages, system_context)
        except Exception as e:
            print(f"ERRO ANTHROPIC: {e}")
            return f"Erro ao acessar Anthropic: {e}"

    def _generate_google(self, messages, system_context=""):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')

            prompt_parts = []
            for m in messages:
                role = "user" if m["role"] in ("user", "system") else "model"
                prompt_parts.append(f"[{role}]: {m['content']}")

            result = model.generate_content("\n".join(prompt_parts))
            return self._post_process(result.text, messages, system_context)
        except Exception as e:
            print(f"ERRO GOOGLE: {e}")
            return f"Erro ao acessar Google Gemini: {e}"

    def generate_streaming(self, prompt_or_messages, system_context=""):
        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            messages = [{"role": "user", "content": prompt_or_messages}]

        if self.provider == "DEEPSEEK":
            yield from self._stream_deepseek(messages)
        else:
            yield from self._stream_mlx(messages)

    def _stream_deepseek(self, messages):
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "stream": True
            }
            with httpx.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60.0) as response:
                buffer = ""
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        content = line[6:]
                        if content == "[DONE]": break
                        try:
                            chunk = json.loads(content)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                buffer += delta
                                if any(c in delta for c in ".!?\n"):
                                    yield buffer.strip()
                                    buffer = ""
                        except: continue
                if buffer: yield buffer.strip()
        except Exception as e:
            yield f"Erro no stream cloud: {e}"

    def _stream_mlx(self, messages):
        from mlx_lm import generate

        self._ensure_stream()
        with self._lock:
            try:
                self._ensure_model_loaded()
                full_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

                response = generate(self.model, self.tokenizer, prompt=full_prompt, max_tokens=600)
                sentences = re.split(r'(?<=[.!?])\s+', response)
                for s in sentences:
                    yield s.strip()
            except Exception as e:
                yield f"Erro no stream local: {e}"

    def _post_process(self, response, original_messages, system_context=""):
        if len(response) > 200:
            lines = response.split(". ")
            if len(lines) > 5:
                from difflib import SequenceMatcher
                ratio = SequenceMatcher(None, lines[-1], lines[-2]).ratio()
                if ratio > 0.8:
                    print("DEBUG: Repeticao detectada. Truncando.")
                    response = ". ".join(lines[:3]) + "."

        # Remove think tags from DeepSeek
        think_open = "<" + "think>"
        think_close = "</" + "think>"
        response = re.sub(r'<(think|reasoning)>.*?</\1>', '', response, flags=re.DOTALL | re.IGNORECASE)
        if think_close in response:
            parts = response.split(think_close)
            response = parts[-1] if parts else response
        response = response.replace(think_open, "").strip()

        is_json = bool(re.search(r'[\[\{].*(tool|action|name).*[\]\}]', response, re.DOTALL))
        if is_json:
            return response

        has_pt_accents = any(c in response for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ")

        pt_no_accents = ["boa", "noite", "bom", "dia", "tudo", "bem", "fazer", "pode", "estou", "aqui", "agora", "ordem", "precisa", "sempre"]
        has_pt_words = any(word in response.lower() for word in pt_no_accents)

        is_probably_english = (len(response) > 40 and not has_pt_accents and not has_pt_words) or                              any(response.lower().startswith(t) for t in ["okay,", "let me", "i will", "the user", "i should", "first,"])

        if is_probably_english and system_context != "TRANSLATION_TASK":
            print(f"DEBUG: Detectado vazamento de Ingles. Corrigindo...")
            translation_prompt = f"Traduza APENAS o significado essencial deste texto para PORTUGUES (BRASIL). Termos tecnicos (API, JSON, etc.) mantenha em ingles: {response[:300]}"
            return self.generate_command(translation_prompt, system_context="TRANSLATION_TASK")

        if response.startswith("{") and response.endswith("}"):
            response = f"[{response}]"

        return response