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
    _lock = threading.RLock() # Lock reentrante para evitar deadlock em traduções recursivas

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LLMManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path="mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"):
        if self._initialized: return
        self.provider = os.getenv("LLM_PROVIDER", "LOCAL").upper()
        self.model_name = os.getenv("LLM_MODEL", model_path)
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        
        # Local MLX specific
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        
        print(f"Cérebro Raciocinante preparado (Provider: {self.provider}, Model: {self.model_name}).")
        self._initialized = True

    def _ensure_model_loaded(self):
        """Carrega o modelo DeepSeek-R1 apenas quando necessário (Local MLX)."""
        if self.provider != "LOCAL" and self.provider != "MLX":
            return

        from core.model_arbiter import arbiter
        if arbiter.request_model("LLM"):
            if self.model is None:
                print(f"Carregando {self.model_path} no Metal...")
                self.model, self.tokenizer = load(self.model_path)
                print("Cérebro DeepSeek-R1 pronto (Local).")

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        if self.provider == "LOCAL" or self.provider == "MLX":
            mx.set_default_stream(mx.default_stream(mx.gpu))

    def generate_command(self, prompt_or_messages, system_context=""):
        """Gera comandos ou respostas usando o provider configurado (.env)."""
        
        # Converte para lista de mensagens se for string
        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            current_ctx = ContextService.get_context_str()
            system_prompt = f"Você é o OMNI, assistente para macOS. Responda em PT-BR de forma concisa.\n{current_ctx}"
            if system_context:
                system_prompt += f"\nCONTEXTO ADICIONAL: {system_context}"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_or_messages}
            ]

        if self.provider == "DEEPSEEK":
            return self._generate_deepseek(messages, system_context)
        else:
            return self._generate_mlx(messages, system_context)

    def _generate_deepseek(self, messages, system_context=""):
        """Chama a API do DeepSeek Cloud."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat", # Ou deepseek-reasoner se preferir
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                print(f"DEBUG CLOUD: Resposta RAW: {content[:100]}...")
                return self._post_process(content, messages, system_context)
        except Exception as e:
            print(f"ERRO DEEPSEEK CLOUD: {e}")
            return f"Erro ao acessar DeepSeek Cloud: {e}"

    def generate_streaming(self, prompt_or_messages, system_context=""):
        """Gera resposta em modo streaming para maior agilidade."""
        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            messages = [{"role": "user", "content": prompt_or_messages}]

        if self.provider == "DEEPSEEK":
            yield from self._stream_deepseek(messages)
        else:
            yield from self._stream_mlx(messages)

    def _stream_deepseek(self, messages):
        """Streaming da API do DeepSeek."""
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
        """Streaming local via MLX."""
        self._ensure_stream()
        with self._lock:
            try:
                self._ensure_model_loaded()
                full_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                
                # Usamos a função nativa de geração com streaming se disponível ou simulamos
                # Para simplificar agora, vamos gerar blocos de texto
                response = generate(self.model, self.tokenizer, prompt=full_prompt, max_tokens=600)
                # Simula streaming por sentenças para manter a compatibilidade da interface
                sentences = re.split(r'(?<=[.!?])\s+', response)
                for s in sentences:
                    yield s.strip()
            except Exception as e:
                yield f"Erro no stream local: {e}"

    def _post_process(self, response, original_messages, system_context=""):
        """Limpeza e filtros comuns a todos os providers."""
        
        # --- REPETITION GUARD ---
        if len(response) > 200:
            lines = response.split(". ")
            if len(lines) > 5:
                from difflib import SequenceMatcher
                ratio = SequenceMatcher(None, lines[-1], lines[-2]).ratio()
                if ratio > 0.8:
                    print("DEBUG: Repetição detectada. Truncando.")
                    response = ". ".join(lines[:3]) + "."

        # Limpeza de CoT
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        if "</think>" in response:
            response = response.split("</think>")[-1].strip()
        response = response.replace("<think>", "").strip()

        # --- SEGURANÇA DE IDIOMA ---
        # Se for um JSON de ferramenta, NÃO TRADUZIMOS (isso quebraria a execução)
        is_json = bool(re.search(r'[\[\{].*tool.*[\]\}]', response, re.DOTALL))
        if is_json:
            return response

        has_pt_accents = any(c in response for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ")
        
        # Palavras comuns em PT-BR que não tem acento (para evitar falso positivo de Inglês)
        pt_no_accents = ["boa", "noite", "bom", "dia", "tudo", "bem", "fazer", "pode", "estou", "aqui", "agora", "ordem", "precisa", "sempre"]
        has_pt_words = any(word in response.lower() for word in pt_no_accents)
        
        english_cot_triggers = ["okay,", "let me", "i will", "the user", "i should", "first,"]
        is_probably_english = (len(response) > 40 and not has_pt_accents and not has_pt_words) or \
                             any(response.lower().startswith(t) for t in english_cot_triggers)
        
        if is_probably_english and system_context != "TRANSLATION_TASK":
            print(f"DEBUG: Detectado vazamento de Inglês. Corrigindo...")
            translation_prompt = f"Traduza APENAS o significado essencial deste texto para PORTUGUÊS (BRASIL): {response[:300]}"
            return self.generate_command(translation_prompt, system_context="TRANSLATION_TASK")

        if response.startswith("{") and response.endswith("}"):
            response = f"[{response}]"

        return response
