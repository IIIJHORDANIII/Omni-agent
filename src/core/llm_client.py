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

load_dotenv()

THINK_OPEN = "<" + "think>"
THINK_CLOSE = "</" + "think>"

class LLMClient:
    def __init__(self):
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
        user_name = os.getenv("USER_NAME", "Senhor").upper()
        
        from core.skill_manager import SkillManager
        active_skill = SkillManager.get_active_skill_prompt()
        return f"""Voce e o ANDERS (estilo JARVIS), assistente pessoal do {user_name}.

REGRAs CRITICAS:
1. PERSISTENCIA: NUNCA desista antes de concluir a tarefa. Se uma ferramenta falhar, tente outra abordagem. Continue executando ferramentas ate QUE a tarefa do usuario esteja COMPLETAMENTE resolvida.
2. RACIOCINIO ReAct: Voce opera em um loop. Comece sua resposta com um bloco de pensamento, depois aja.
3. ACAO: Apos o pensamento, coloque APENAS a chamada de ferramenta EM UM UNICO BLOCO JSON usando ESTRITAMENTE o formato: {{"tool": "nome_da_ferramenta", "arguments": {{"param": "valor"}}}}. NAO use outro formato! NAO inclua texto antes ou depois do JSON.
4. IDIOMA: Responda SEMPRE em Portugues (Brasil). Termos tecnicos que nao possuem traducao direta ou que sao padrao na industria (API, JSON, PR, Issue, Deploy, Pull Request, Commit, Merge, etc.) voce DEVE manter em ingles. NUNCA tente traduzi-los.
5. RESPOSTA FINAL: So responda ao usuario (sem JSON) quando a tarefa estiver CONCLUIDA e todas as ferramentas ja foram executadas.
6. VERIFICACAO DE ACAO (REGRA DE OURO): Se o usuario pediu para "criar", "salvar", "enviar", "adicionar", "colocar", "agendar" ou "executar" qualquer acao produtiva (Notas, Emails, Lembretes, Calendario, PRs, Arquivos, etc.), voce DEVE obrigatoriamente executar a ferramenta correspondente ANTES de dar a resposta final. NUNCA diga que fez algo sem ter o SUCCESS da ferramenta.
7. PERSISTENCIA EM ERRO: Se uma ferramenta retornar FAILURE, nao desista. Tente corrigir os parametros ou usar uma ferramenta alternativa (ex: se create_note falhar, tente run_shell para criar um arquivo). So finalize apos sucesso real.
8. Create_note: Para criar notas no app Notas do macOS, use create_note com title e content.
9. NAO ALUCINE: Se o input do usuario for vago, curto, sem sentido, ou nao pedir nenhuma acao especifica, responda APENAS com uma saudacao curta. NUNCA execute ferramentas ou acoes nao solicitadas. NUNCA invente tarefas.
10. VOZ PRIMEIRO: Voce e um assistente de VOZ. Nunca repita o que vai fazer — apenas FAÇA. Exemplo ERRADO: "Claro! Vou abrir o app Notas para voce." {{ json }} Exemplo CORRETO: {{ json }}
11. NOME DO USUARIO: O nome do seu mestre e {user_name}. Mesmo que ele te chame por outros nomes no comando (como Dominique ou Jarvis), voce deve se referir a ele apenas como {user_name} ou "Senhor".
12. EMPIRISMO (OBRIGATORIO): NUNCA confie no historico para saber se um app/site esta aberto. O usuario pode ter fechado a janela logo apos voce abrir. Se o usuario pedir para abrir algo, EXECUTE a ferramenta novamente, mesmo que voce ache que ja fez.
13. CONFIRMACAO VISUAL: Se o usuario disser que algo "nao abriu" ou pedir para voce "conferir", voce DEVE obrigatoriamente usar a ferramenta analyze_screen() para ver o que esta acontecendo antes de responder. NUNCA diga "ja abri" sem ver a tela se o usuario estiver contestando.
14. NAO SEJA REPETITIVO: Nao diga "O Linear ja esta aberto" se o usuario acabou de dizer que nao esta. Peça desculpas e tente uma abordagem diferente (ex: abrir via run_shell ou conferir a tela).

LISTA DE FERRAMENTAS DISPONIVEIS:
- vscode_sync(): Descobre qual arquivo e projeto esta aberto no VS Code agora.
- auto_github_pr(title, body): Cria um PR no GitHub automaticamente.
- smart_search(query): Busca FUZZY/INTELIGENTE em todo o Mac via Spotlight.
- memory_query(key): Busca na memoria de longo prazo.
- memory_write(key, value): Salva um fato importante.
- resolve_path(name): Busca uma pasta no Mac.
- open_app(app, path): Abre um app.
- open_url(url): Abre um site NO NAVEGADOR PADRAO. NUNCA passe o parametro browser.
- web_search(query): Busca na web e resume resultados.
- mail_unread(count): E-mails nao lidos de hoje.
- mail_draft(subject, body, recipient): Cria rascunho de e-mail.
- github_pr_details(repo, pr): Detalhes de PRs do GitHub.
- linear_my_issues(): Suas tarefas no Linear.
- analyze_screen(): Ve a tela agora.
- notes_search(query): Busca notas no app Notas do macOS.
- create_note(title, content): Cria uma nota real no app Notas do macOS.
- generate_image(prompt): Gera imagem IA localmente.
- swarm_solve(task): Ativa sub-agentes para problemas complexos.
- vision_action(action, x, y, text): Age fisicamente na tela.
- run_shell(command): Executa shell no Mac.

DADOS DO MAC:
{ctx}

ALIASED: 
- PPRD, PJ ou PAYJOTA = repositorio weboptionwp/app-payjota.
- LOCAL_PJ = pasta /Users/pastorello/Documents/payjota/app-payjota (use para run_shell se necessario).
- AGENT = este projeto atual.
"""

    def _summarize_history(self, old_messages):
        resume = []
        for msg in old_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            content = content[:200]
            if role == "tool" or "RESULTADO DA FERRAMENTA" in content:
                resume.append(f"[Ferramenta]: {content}")
            else:
                resume.append(f"[{role}]: {content}")
        return "\n".join(resume[-6:])

    def _clean_response(self, text, is_translation_pass=False):
        if not text:
            return ""

        json_match = re.search(r'[\[\{].*(?:tool|action|name|arguments).*[\]\}]', text, re.DOTALL)
        if json_match and not is_translation_pass:
            before = text[:json_match.start()].strip()
            if before and len(before) < 200:
                print(f"LLM: Texto descartado antes do JSON: '{before[:80]}...'")
            return text[json_match.start():json_match.end()].strip()

        clean_text = re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)

        if THINK_CLOSE in clean_text:
            parts = clean_text.split(THINK_CLOSE)
            clean_text = parts[-1] if parts else clean_text
        clean_text = clean_text.replace(THINK_OPEN, "")

        patterns_to_remove = [
            r'^Pensamento:.*?\n',
            r'^Raciocinio:.*?\n',
            r'^Thought:.*?\n',
            r'\n\nPensamento:.*',
            r'\n\nThought:.*'
        ]
        for pattern in patterns_to_remove:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)

        return clean_text.strip()

    def chat(self, messages, include_vision=False, image_b64=None, stream_callback=None):
        try:
            last_message = messages[-1]["content"] if messages else ""
            
            full_messages = []
            
            semantic_context = self.semantic_memory.get_context_for_prompt(last_message)
            
            system_prompt = self.get_system_prompt()
            if semantic_context:
                system_prompt += f"\n{semantic_context}"
            
            if include_vision:
                vision_prompt = f"Descreva detalhadamente o que esta na tela, focando em: {last_message}"
                visual_description = self.vision_service.describe_screen(vision_prompt)
                system_prompt += f"\n\nCONTEXTO_VISUAL (Qwen2-VL): {visual_description}"
            
            full_messages.append({"role": "system", "content": system_prompt})
            
            MAX_CONTEXT = 8
            
            if len(messages) > MAX_CONTEXT:
                print("DEBUG LLM: Historico longo detectado. Resumindo contexto...")
                summary = self._summarize_history(messages[:-MAX_CONTEXT])
                context_history = [{"role": "system", "content": f"Contexto anterior resumido:\n{summary}"}] + messages[-MAX_CONTEXT:]
            else:
                context_history = messages
            
            full_messages.extend(context_history)
            
            print(f"DEBUG LLM: Iniciando geracao (ReAct Loop)...")
            
            max_iterations = 12
            iteration = 0
            final_response = ""
            
            while iteration < max_iterations:
                iteration += 1
                
                answer_raw = self.manager.generate_command(full_messages)
                answer = self._clean_response(answer_raw)
                
                # Suporta formatos: {"tool": ...}, {"action": ...} ou {"name": ..., "arguments": ...}
                has_json = "{" in answer and any(k in answer for k in ["tool", "action", "name"])
                
                if has_json:
                    print(f"DEBUG: Iteracao {iteration} - Ferramenta detectada.")
                    full_messages.append({"role": "assistant", "content": answer})
                    
                    tool_result = ToolDispatcher.dispatch(answer)
                    tool_result_str = str(tool_result)
                    if len(tool_result_str) > 500:
                        tool_result_str = tool_result_str[:500] + "..."
                    
                    full_messages.append({
                        "role": "user",
                        "content": f"RESULTADO DA FERRAMENTA:\n{tool_result_str}\nSe a tarefa NAO terminou, use OUTRA ferramenta. Se terminou, de a resposta final ao usuario (sem JSON)."
                    })
                    
                    if len(full_messages) > 20:
                        system_msg = full_messages[0]
                        recent = full_messages[-14:]
                        history_summary = self._summarize_history(full_messages[1:-14])
                        full_messages.clear()
                        full_messages.append(system_msg)
                        full_messages.append({"role": "system", "content": f"Contexto anterior resumido:\n{history_summary}"})
                        full_messages.extend(recent)
                    
                    if "FAILURE" in str(tool_result):
                        from core.registry import registry
                        hud = registry.get("hud")
                        if hud:
                            hud.display_signal.emit("CORRIGINDO ERRO INTERNO...", "THINKING", 2000)
                    
                    if iteration == 1:
                        threading.Thread(
                            target=self.evolution.evaluate_and_evolve,
                            args=(last_message, answer, str(tool_result)),
                            daemon=True
                        ).start()
                else:
                    print(f"DEBUG: Iteracao {iteration} - Resposta final recebida.")
                    if stream_callback:
                        stream_callback(answer)
                    final_response = answer
                    break
                    
            if not final_response:
                print(f"DEBUG: Limite de {max_iterations} iteracoes atingido. Forcando resposta final...")
                summary_msg = {"role": "user", "content": "Voce atingiu o limite de iteracoes. Resuma O QUE VOCE JA FEZ e finalize a resposta agora em portugues. Se a tarefa foi parcialmente concluida, explique o que faltou."}
                full_messages.append(summary_msg)
                try:
                    forced_response = self.manager.generate_command(full_messages, system_context="FINAL_SUMMARY")
                    final_response = self._clean_response(forced_response)
                except:
                    final_response = "Consegui executar parte da tarefa, mas atingi o limite de passos. Por favor, peca novamente para continuarmos de onde parei."
            
            from core.llm_manager import LLMManager as _LM
            if _LM._detect_provider() in ("LOCAL", "MLX"):
                import mlx.core as mx
                mx.clear_cache()
            return final_response.strip()
            
        except Exception as e:
            print(f"ERRO LLM: {e}")
            return f"Erro na execucao da LLM. Verifique os logs do sistema."
