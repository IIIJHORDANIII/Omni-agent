import threading
import os
from mlx_lm import load, generate
import mlx.core as mx
from core.context_service import ContextService

class LLMManager:
    _instance = None
    _thread_local = threading.local()
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LLMManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path="mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"):
        if self._initialized: return
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        print(f"Cérebro Raciocinante preparado ({model_path}).")
        self._initialized = True

    def _ensure_model_loaded(self):
        """Carrega o modelo DeepSeek-R1 apenas quando necessário."""
        if self.model is None:
            import gc
            gc.collect()
            try:
                mx.clear_cache()
            except: pass

            print(f"Carregando {self.model_path} no Metal...")
            self.model, self.tokenizer = load(self.model_path)
            print("Cérebro DeepSeek-R1 pronto.")

    def _ensure_stream(self):
        """Garante que a thread atual tenha o stream default da GPU bound."""
        # Define o stream default para a thread atual como o stream default da GPU
        mx.set_default_stream(mx.default_stream(mx.gpu))

    def generate_command(self, prompt_or_messages, system_context=""):
        """Gera comandos ou respostas usando o modelo MLX. Aceita string ou lista de mensagens."""
        self._ensure_stream()
        with self._lock:
            try:
                # Usa o stream default da GPU de forma explícita
                with mx.stream(mx.default_stream(mx.gpu)):
                    self._ensure_model_loaded()
                    
                    if isinstance(prompt_or_messages, list):
                        messages = prompt_or_messages
                    else:
                        # Contexto minimalista se for apenas um prompt solto
                        current_ctx = ContextService.get_context_str()
                        system_prompt = f"Você é o OMNI, assistente para macOS. Responda em PT-BR de forma concisa.\n{current_ctx}"
                        if system_context:
                            system_prompt += f"\nCONTEXTO ADICIONAL: {system_context}"
                            
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt_or_messages}
                        ]
                    
                    if hasattr(self.tokenizer, "apply_chat_template"):
                        full_prompt = self.tokenizer.apply_chat_template(
                            messages, tokenize=False, add_generation_prompt=True
                        )
                    else:
                        # Fallback básico
                        full_prompt = ""
                        for msg in messages:
                            role = msg['role']
                            content = msg['content']
                            full_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
                        full_prompt += "<|im_start|>assistant\n"

                    response = generate(self.model, self.tokenizer, prompt=full_prompt, max_tokens=600, verbose=False)

                    if response is None:
                        return "Não consegui processar seu pedido agora."

                    response = response.strip()
                    
                    # Limpeza de blocos de raciocínio (DeepSeek-R1 / Think tags)
                    import re
                    # 1. Remove tudo entre <think> e </think>
                    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
                    # 2. Caso o modelo tenha esquecido de fechar a tag ou começou direto no pensamento
                    if "</think>" in response:
                        response = response.split("</think>")[-1].strip()
                    response = response.replace("<think>", "").strip()

                    # --- SEGURANÇA DE IDIOMA E LIMPEZA DE COT ---
                    # Se o texto for longo e não tiver acentos, ou começar com CoT em inglês, traduzimos.
                    has_pt_accents = any(c in response for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ")
                    english_cot_triggers = ["okay,", "let me", "i will", "the user", "i should", "first,"]
                    is_probably_english = (len(response) > 40 and not has_pt_accents) or \
                                         any(response.lower().startswith(t) for t in english_cot_triggers)
                    
                    if is_probably_english and system_context != "TRANSLATION_TASK":
                        print(f"DEBUG: Detectado vazamento de Inglês/CoT no Manager. Corrigindo...")
                        # Tenta extrair apenas a parte que parece PT se houver
                        if has_pt_accents:
                            parts = re.split(r'[.!?]\s+', response)
                            pt_parts = [p for p in parts if any(c in p for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ")]
                            if pt_parts:
                                return " ".join(pt_parts).strip()

                        # Se for puramente inglês, solicita tradução interna (recursão controlada)
                        translation_prompt = f"Traduza este pensamento para PORTUGUÊS (BRASIL) de forma natural e concisa. Responda APENAS a tradução: {response}"
                        # Evita recursão infinita passando um contexto especial
                        return self.generate_command(translation_prompt, system_context="TRANSLATION_TASK")

                    # Correção automática de formato JSON
                    if response.startswith("{") and response.endswith("}"):
                        response = f"[{response}]"

                    return response
            except Exception as e:
                print(f"ERRO LLM: {e}")
                return f"Erro na geração: {e}"
