import os
import re
import json
from dotenv import load_dotenv
from core.execution_service import ExecutionService
from core.memory_client import MemoryClient
from core.web_service import WebService
from core.document_service import DocumentService
from core.vision_service import VisionService
from core.context_service import ContextService
from core.tool_dispatcher import ToolDispatcher
from core.llm_manager import LLMManager

# Carrega variáveis de ambiente
load_dotenv()

class LLMClient:
    def __init__(self):
        # Usamos o MLX Manager nativo por padrão
        self.manager = LLMManager()
        
        self.execution_service = ExecutionService()
        self.memory_client = MemoryClient()
        self.vision_service = VisionService()
        self.web_service = WebService(llm_manager=self.manager, vision=self.vision_service)
        self.document_service = DocumentService()

    def get_system_prompt(self):
        ctx = ContextService.get_context_str()
        return f"""Você é o OMNISCIENT, assistente autônomo total para macOS com RACIOCÍNIO DeepSeek-R1.

REGRAS DE OURO (SÃO PROTOCOLOS DE SEGURANÇA):
1. PENSE internamente antes de agir dentro de <think>...</think>.
2. RESPOSTA FINAL DEVE SER 100% EM PORTUGUÊS (BRASIL).
3. QUALQUER PALAVRA EM INGLÊS FORA DO <think> É UMA FALHA DE PROTOCOLO.
4. Se pedirem algo da INTERNET, use `web_read` ou `web_search`.
5. Se pedirem algo do MAC, use `project_summary` ou `list_files`.
6. Responda em JSON para ações: [{{"tool": "nome", "params": {{...}} }}].
7. Se for apenas conversa, responda de forma curta em PT-BR.
"""

    def _clean_response(self, text, is_translation_pass=False):
        if not text: return ""
        
        # 1. Limpeza agressiva de tags de pensamento
        clean_text = text.replace('</think>', ' </think> ').strip() # Garante espaço para split se necessário
        
        if "<think>" in clean_text:
            if "</think>" in clean_text:
                parts = clean_text.split("</think>")
                clean_text = parts[-1].strip()
            else:
                # Tag aberta mas não fechada
                start_idx = clean_text.find("<think>")
                json_start = clean_text.find("[", start_idx)
                if json_start == -1: json_start = clean_text.find("{", start_idx)
                
                if json_start != -1:
                    clean_text = clean_text[json_start:]
                else:
                    lines = [l.strip() for l in clean_text[start_idx+7:].split("\n") if l.strip()]
                    for line in reversed(lines):
                        if any(c in line for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ"):
                            return line
                    return ""
        elif "</think>" in clean_text:
            # Caso raro: Modelo gera apenas a tag de fechamento ou começa por ela
            clean_text = clean_text.split("</think>")[-1].strip()
        
        clean_text = clean_text.strip()
        if not clean_text: return ""

        # 2. Detecção de Idioma e Meta-Talk
        # Verificamos se há acentos típicos de PT-BR
        has_pt_accents = any(c in clean_text for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ")
        
        # Palavras em inglês que frequentemente vazam em respostas "Portu-glish"
        english_leaks = ["developed", "below", "company", "application", "interact", "command", "task", "features"]
        has_english_leak = any(word in clean_text.lower() for word in english_leaks)
        
        english_meta_triggers = (
            "okay", "i will", "the user", "i should", "first", "second", "i'll", "i'm", 
            "here is", "sure", "i found", "i see", "let me", "i can", "of course", 
            "based on", "to answer", "i need to", "i will now", "the request"
        )
        
        lower_text = clean_text.lower()
        starts_with_meta = any(lower_text.startswith(t) for t in english_meta_triggers)

        # Se não é um passe de tradução e não tem acentos em um texto longo, ou começa com meta-talk, ou tem vazamento
        if not is_translation_pass:
            # Caso A: JSON detectado (prioridade máxima)
            json_match = re.search(r'[\[\{].*tool.*[\]\}]', clean_text, re.DOTALL)
            if json_match:
                return clean_text[json_match.start():].strip()

            # Caso B: Texto com problemas de idioma
            if (len(clean_text) > 40 and not has_pt_accents) or starts_with_meta or (has_pt_accents and has_english_leak):
                # Tenta extrair frases que pareçam PT puro (acentuadas e sem leaks)
                sentences = re.split(r'(?<=[.!?])\s+', clean_text)
                pt_sentences = []
                for s in sentences:
                    if any(c in s for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ") and not any(w in s.lower() for w in english_leaks):
                        pt_sentences.append(s.strip())
                
                if pt_sentences and not starts_with_meta:
                    return " ".join(pt_sentences)
                
                # Se o texto está muito "sujo", sinaliza necessidade de tradução total
                return f"__NEED_TRANSLATION__{clean_text}"

        return clean_text.strip()

    def chat(self, messages, include_vision=False, image_b64=None):
        try:
            last_message = messages[-1]["content"] if messages else ""
            
            # 1. Constrói o histórico com o System Prompt no topo
            full_messages = []
            system_prompt = self.get_system_prompt()
            
            if include_vision:
                vision_prompt = f"Descreva detalhadamente o que está na tela, focando em: {last_message}"
                visual_description = self.vision_service.describe_screen(vision_prompt)
                system_prompt += f"\n\nCONTEXTO_VISUAL (Qwen2-VL): {visual_description}"
            
            full_messages.append({"role": "system", "content": system_prompt})
            
            # Adiciona apenas as últimas 10 mensagens para não estourar o contexto
            full_messages.extend(messages[-10:])
            
            print(f"DEBUG LLM: Enviando histórico para o DeepSeek-R1...")
            answer = self.manager.generate_command(full_messages)
            
            clean_answer = self._clean_response(answer)
            
            # MECANISMO DE TRADUÇÃO PARA RESPOSTA DIRETA
            is_english = clean_answer.startswith("__NEED_TRANSLATION__") or (len(clean_answer) > 40 and not any(c in clean_answer for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ"))
            
            if is_english:
                 original_text = clean_answer.replace("__NEED_TRANSLATION__", "")
                 print(f"DEBUG: Texto em Inglês detectado. Traduzindo...")
                 translation_prompt = f"Traduza este texto para PORTUGUÊS (BRASIL). Responda APENAS a tradução direta, sem comentários: {original_text}"
                 translated = self.manager.generate_command(translation_prompt, system_context="SISTEMA_DE_TRADUCAO_PURAMENTE_EM_PORTUGUES_SEM_META_TALK")
                 clean_answer = self._clean_response(translated, is_translation_pass=True)

            has_json = "{" in clean_answer and ("tool" in clean_answer or "action" in clean_answer)
            
            if has_json:
                print(f"DEBUG: JSON detectado. Executando...")
                tool_result = ToolDispatcher.dispatch(clean_answer)
                
                # 2. Segunda Passada (Síntese) - Aqui usamos o histórico também
                synthesis_messages = full_messages.copy()
                synthesis_messages.append({"role": "assistant", "content": clean_answer})
                synthesis_messages.append({"role": "user", "content": f"Resultado das ferramentas: {tool_result}. Agora responda ao usuário de forma natural em PT-BR."})
                
                final_response_raw = self.manager.generate_command(synthesis_messages)
                final_response = self._clean_response(final_response_raw)
                
                # MECANISMO DE TRADUÇÃO PARA SÍNTESE
                is_synth_english = final_response.startswith("__NEED_TRANSLATION__") or (len(final_response) > 40 and not any(c in final_response for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ"))
                
                if is_synth_english:
                    original_text = final_response.replace("__NEED_TRANSLATION__", "")
                    print("DEBUG: Síntese em Inglês detectada. Traduzindo...")
                    translation_prompt = f"Traduza este texto para PORTUGUÊS (BRASIL). Responda APENAS a tradução: {original_text}"
                    translated = self.manager.generate_command(translation_prompt, system_context="SISTEMA_DE_TRADUCAO_PURAMENTE_EM_PORTUGUES_SEM_META_TALK")
                    final_response = self._clean_response(translated, is_translation_pass=True)

                import mlx.core as mx
                mx.clear_cache()
                return final_response.strip()
            
            return clean_answer.strip()
        except Exception as e:
            print(f"ERRO MLX: {e}")
            return f"Erro na execução local via MLX. Verifique os logs do sistema."
