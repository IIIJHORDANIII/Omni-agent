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

        # Registro no Arbiter
        from core.model_arbiter import arbiter
        arbiter.register_unloader("LLM", self.unload_model)

    def unload_model(self):
        if self.model:
            print(f"LLMManager: Descarregando {self.model_path} da RAM...")
            self.model = None
            self.tokenizer = None

    def _ensure_model_loaded(self):
        """Carrega o modelo DeepSeek-R1 apenas quando necessário (Local MLX)."""
        if self.provider != "LOCAL" and self.provider != "MLX":
            return

        if self.model is None:
            import gc
            gc.collect()
            try:
                mx.clear_cache()
            except: pass

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

    def _generate_mlx(self, messages, system_context=""):
        """Gera resposta usando MLX local."""
        self._ensure_stream()
        with self._lock:
            try:
                with mx.stream(mx.default_stream(mx.gpu)):
                    self._ensure_model_loaded()
                    
                    if hasattr(self.tokenizer, "apply_chat_template"):
                        full_prompt = self.tokenizer.apply_chat_template(
                            messages, tokenize=False, add_generation_prompt=True
                        )
                    else:
                        full_prompt = ""
                        for msg in messages:
                            role = msg['role']
                            content = msg['content']
                            full_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
                        full_prompt += "<|im_start|>assistant\n"

                    response = generate(self.model, self.tokenizer, prompt=full_prompt, max_tokens=600, verbose=False)
                    print(f"DEBUG MLX: Resposta RAW: {response[:100]}...")
                    
                    if response is None:
                        return "Não consegui processar seu pedido agora."
                        
                    return self._post_process(response.strip(), messages, system_context)
            except Exception as e:
                print(f"ERRO MLX: {e}")
                return f"Erro na geração local: {e}"

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
        english_cot_triggers = ["okay,", "let me", "i will", "the user", "i should", "first,"]
        is_probably_english = (len(response) > 40 and not has_pt_accents) or \
                             any(response.lower().startswith(t) for t in english_cot_triggers)
        
        if is_probably_english and system_context != "TRANSLATION_TASK":
            print(f"DEBUG: Detectado vazamento de Inglês. Corrigindo...")
            translation_prompt = f"Traduza APENAS o significado essencial deste texto para PORTUGUÊS (BRASIL): {response[:300]}"
            return self.generate_command(translation_prompt, system_context="TRANSLATION_TASK")

        if response.startswith("{") and response.endswith("}"):
            response = f"[{response}]"

        return response
