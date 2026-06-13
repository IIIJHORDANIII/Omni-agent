import os
import re
import json
import threading
from dotenv import load_dotenv
from core.execution_service import ExecutionService
from core.memory_client import MemoryClient
from core.web_service import WebService
from core.document_service import DocumentService
from core.vision_service import VisionService
from core.context_service import ContextService
from core.tool_dispatcher import ToolDispatcher
from core.llm_manager import LLMManager
from core.semantic_memory import SemanticMemory
from core.evolution_service import EvolutionService
from core.mcp_client import MCPClient
from core.crawler_service import ProjectCrawlerService
from core.swarm_manager import SwarmManager
from core.computer_use import ComputerUseService

# Carrega variáveis de ambiente
load_dotenv()

class LLMClient:
    def __init__(self):
        # Usamos o MLX Manager nativo por padrão
        self.manager = LLMManager()
        self.semantic_memory = SemanticMemory()
        self.evolution = EvolutionService(self.manager)
        self.mcp = MCPClient()
        self.crawler = ProjectCrawlerService(self.manager)
        self.swarm = SwarmManager(self.manager)
        self.computer = ComputerUseService()
        
        self.execution_service = ExecutionService()
        self.memory_client = MemoryClient()
        self.vision_service = VisionService()
        self.web_service = WebService(llm_manager=self.manager, vision=self.vision_service)
        self.document_service = DocumentService()

    def get_system_prompt(self):
        ctx = ContextService.get_context_str()
        
        # Injeta Habilidade Ativa (agent-skills) se houver
        from core.skill_manager import SkillManager
        active_skill = SkillManager.get_active_skill_prompt()
        return f"""Você é o OMNISCIENT (estilo JARVIS), assistente pessoal do JHORDAN PASTORELLO.

REGRAS CRÍTICAS:
1. PENSAMENTO INTUITIVO: Antes de qualquer ação, pare e pense. Use ferramentas de busca se faltar contexto.
2. RACIOCÍNIO SOTA (ReAct): Você opera em um loop. OBRIGATORIAMENTE comece sua resposta com um bloco `<think> ... </think>` explicando sua lógica passo a passo.
3. AÇÃO: Após o pensamento, se precisar agir, coloque a chamada de ferramenta EM UM ÚNICO BLOCO JSON.
   EXEMPLO DE RESPOSTA COM FERRAMENTA:
   <think>
   1. Preciso achar o arquivo.
   2. Vou usar a busca inteligente.
   </think>
   [{{\"tool\": \"smart_search\", \"params\": {{\"query\": \"projeto\"}}}}]
4. IDIOMA: Responda SEMPRE em Português (Brasil) natural e elegante.
5. RESPOSTA FINAL: Se não precisar de mais ferramentas, responda ao usuário (sem JSON).

LISTA DE FERRAMENTAS DISPONÍVEIS:
- vscode_sync(): Descobre qual arquivo e projeto está aberto no VS Code agora.
- auto_github_pr(title, body): Cria um PR no GitHub automaticamente.
- smart_search(query): Busca FUZZY/INTELIGENTE em todo o Mac via Spotlight.
- memory_query(key): Busca na memória de longo prazo.
- memory_write(key, value): Salva um fato importante.
- resolve_path(name): Busca uma pasta no Mac.
- open_app(app, path): Abre um app.
- open_url(url, browser): Abre um site.
- web_search(query): Busca na web.
- mail_unread(count): E-mails não lidos de hoje.
- mail_draft(subject, body, recipient): Cria rascunho de e-mail.
- github_pr_details(repo, pr): Detalhes de PRs.
- linear_my_issues(): Suas tarefas no Linear.
- analyze_screen(): Vê a tela agora.
- notes_search(query): Busca notas no app Notas.
- create_note(title, content): Cria uma nota real no macOS.
- generate_image(prompt): Gera imagem IA localmente.
- swarm_solve(task): Ativa sub-agentes para problemas complexos.
- vision_action(action, x, y, text): Age fisicamente na tela.
- run_shell(command): Executa shell no Mac. Use PersistentShell para manter estado de diretório.

DADOS DO MAC:
{ctx}

ALIASED: 
- PPRD = repositório weboptionwp/app-payjota.
- PJ ou PAYJOTA = pasta /Users/pastorello/Documents/pessoal/agent ou similar em Documents.
- FPJ = subpasta de projeto dentro de PJ.
"""


    def _clean_response(self, text, is_translation_pass=False):
        if not text: return ""
        
        # 1. Extração de JSON se presente (Prioridade máxima no loop ReAct)
        json_match = re.search(r'[\[\{].*(tool|action).*[\]\}]', text, re.DOTALL)
        if json_match and not is_translation_pass:
            return text[json_match.start():json_match.end()].strip()

        # 2. Limpeza agressiva de tags e marcadores de pensamento
        # Remove blocos <think>...</think> ou <reasoning>...</reasoning>
        clean_text = re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove marcadores de texto comuns que o DeepSeek ou outros modelos usam às vezes
        patterns_to_remove = [
            r'^Pensamento:.*?\n', 
            r'^Raciocínio:.*?\n', 
            r'^Thought:.*?\n',
            r'\n\nPensamento:.*',
            r'\n\nThought:.*'
        ]
        for pattern in patterns_to_remove:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)

        # Caso a tag não tenha sido fechada (streaming ou erro de geração)
        if "<think>" in clean_text.lower():
            clean_text = clean_text.lower().split("<think>")[0]
            
        return clean_text.strip()

    def chat(self, messages, include_vision=False, image_b64=None, stream_callback=None):
        try:
            last_message = messages[-1]["content"] if messages else ""
            
            # 1. Constrói o histórico com o System Prompt no topo
            full_messages = []
            
            # RECUPERAÇÃO SEMÂNTICA (RAG): Busca fatos relevantes na memória baseados na mensagem atual
            semantic_context = self.semantic_memory.get_context_for_prompt(last_message)
            
            system_prompt = self.get_system_prompt()
            if semantic_context:
                system_prompt += f"\n{semantic_context}"
            
            if include_vision:
                vision_prompt = f"Descreva detalhadamente o que está na tela, focando em: {last_message}"
                visual_description = self.vision_service.describe_screen(vision_prompt)
                system_prompt += f"\n\nCONTEXTO_VISUAL (Qwen2-VL): {visual_description}"
            
            full_messages.append({"role": "system", "content": system_prompt})
            
            # GESTÃO DE CONTEXTO: Resume histórico se for muito longo
            if len(messages) > 12:
                print("DEBUG LLM: Histórico longo detectado. Resumindo contexto...")
                summary_prompt = "Resuma o histórico desta conversa em 3 pontos chave para manter o contexto principal vivo."
                # ... Lógica de resumo aqui ...
                context_history = messages[-10:]
            else:
                context_history = messages[-10:]
            
            full_messages.extend(context_history)
            
            print(f"DEBUG LLM: Iniciando geração (ReAct Loop)...")
            
            max_iterations = 5
            iteration = 0
            final_response = ""
            
            while iteration < max_iterations:
                iteration += 1
                
                answer_raw = self.manager.generate_command(full_messages)
                answer = self._clean_response(answer_raw)
                
                # Verifica se há chamada de ferramenta
                has_json = "{" in answer and ("tool" in answer or "action" in answer)
                
                if has_json:
                    print(f"DEBUG: Iteração {iteration} - Ferramenta detectada.")
                    # Adiciona a ação do assistente ao histórico da iteração
                    full_messages.append({"role": "assistant", "content": answer})
                    
                    # Executa a ferramenta
                    tool_result = ToolDispatcher.dispatch(answer)
                    
                    # Devolve o resultado como 'user' (feedback)
                    full_messages.append({
                        "role": "user", 
                        "content": f"RESULTADO DA FERRAMENTA:\n{tool_result}\nSe a tarefa não terminou ou falhou, use outra estratégia/ferramenta. Se terminou, dê a resposta final (sem JSON)."
                    })
                    
                    # Feedback visual se houver falha na ferramenta (Fase 5 - Transparência)
                    if "FAILURE" in str(tool_result):
                        from core.registry import registry
                        hud = registry.get("hud")
                        if hud:
                            hud.display_signal.emit("CORRIGINDO ERRO INTERNO...", "THINKING", 2000)
                    
                    # Auto-Evolução (apenas na primeira iteração para manter simples)
                    if iteration == 1:
                        threading.Thread(
                            target=self.evolution.evaluate_and_evolve, 
                            args=(last_message, answer, str(tool_result)),
                            daemon=True
                        ).start()
                else:
                    print(f"DEBUG: Iteração {iteration} - Resposta final recebida.")
                    # Se houver stream callback configurado e for a resposta final, podemos emitir (mas para manter simples o loop ReAct, não usamos streaming interno)
                    if stream_callback:
                        stream_callback(answer)
                    final_response = answer
                    break
                    
            if not final_response:
                final_response = "Atingi o limite de iterações tentando resolver a tarefa."
                
            import mlx.core as mx
            mx.clear_cache()
            return final_response.strip()
            
        except Exception as e:
            print(f"ERRO LLM: {e}")
            return f"Erro na execução da LLM. Verifique os logs do sistema."
