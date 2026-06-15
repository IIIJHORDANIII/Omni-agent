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
        return f"""Você é o OMNISCIENT, assistente pessoal para macOS.

PROTOCOLO DE RESPOSTA (OBRIGATÓRIO):
1. <think> Sua análise interna (qualquer idioma). </think>
2. RESPOSTA FINAL: Apenas Português (Brasil).
3. AÇÕES: Se precisar usar uma ferramenta, você PODE falar uma frase curta em PT-BR e DEVE incluir o JSON: [{{"tool": "nome", "params": {{...}} }}].
4. PROIBIDO: Explicar quem você é ou usar meta-conversa (ex: "Entendido, vou fazer...").
5. Se for apenas conversa, seja direto e amigável.

LISTA DE FERRAMENTAS DISPONÍVEIS:
- open_app(app): Abre um app no Mac.
- open_url(url): Abre um site ou link.
- control_app(app, action): UI Scripting (ex: click menu "File").
- web_search(query): Busca na web e resume.
- web_read(url): Lê o conteúdo de uma página web.
- mail_unread(count): E-mails não lidos de hoje.
- mail_search(query): Busca e-mails por assunto/remetente.
- mail_draft(subject, body, recipient): Cria rascunho de e-mail.
- notes_search(query): Busca nas Notas do macOS.
- create_note(title, content): Cria nota ou arquivo de texto (.txt).
- list_files(path): Lista arquivos de um diretório.
- read_file(path): Lê o conteúdo de um arquivo.
- analyze_screen(): Descreve o que está na tela agora.
- get_calendar_events(): Eventos do calendário de hoje.
- get_reminders(): Lembretes pendentes.
- add_reminder(title): Adiciona lembrete.
- set_volume(level): Ajusta volume do sistema (0-100).
- run_shell(command): Executa comando no terminal macOS.
- run_python(code): Executa código Python em sandbox.
- run_tests(path): Roda testes (pytest, npm, cargo).
- github_commits(repo): Commits recentes de um repo.
- github_list_prs(repo): Lista Pull Requests abertos.
- github_create_pr(repo, title, head, base, body): Cria um PR no GitHub.
- linear_my_issues(): Suas tarefas pendentes no Linear.
- linear_cycle: Resumo do ciclo atual do Linear.
- project_summary(path): Resumo técnico do projeto (Git + Logs).
- manage_music(app, action): Controla Spotify/Music (play, pause, next).
- get_system_info(): Status de bateria e disco.
- move_window(app, x, y, w, h): Move janela via Swift.
- toggle_mute(): Alterna mudo do microfone.
- run_shortcut(name, input): Executa um Atalho do macOS.
- list_shortcuts(): Lista todos os seus Atalhos salvos.
- set_focus(mode): Ativa um Modo de Foco (ex: "Não Perturbe", "Trabalho").
- screenshot(path): Tira um print da tela inteira.
- download_file(url, path): Baixa um arquivo ou imagem da internet.
- generate_image(prompt, output): Gera uma imagem via Stable Diffusion local.
- media_cut(input, start, duration, output): Corta vídeo/áudio via FFmpeg (start: "00:00:10").
- media_to_mp3(input, output): Converte arquivo de mídia para MP3.
- create_tool(requirement): Protocolo Gênesis (Cria ferramenta do zero).

CONTEXTO DO MAC:
{ctx}
"""


    def _clean_response(self, text, is_translation_pass=False):
        if not text: return ""
        
        # 1. Limpeza agressiva de tags de pensamento
        clean_text = text.replace('</think>', ' </think> ').strip()
        
        if "<think>" in clean_text:
            if "</think>" in clean_text:
                parts = clean_text.split("</think>")
                clean_text = parts[-1].strip()
            else:
                # Se não fechou, tenta pegar o que vem depois do início do pensamento ou o primeiro JSON
                start_idx = clean_text.find("<think>")
                json_start = clean_text.find("[", start_idx)
                if json_start != -1:
                    clean_text = clean_text[json_start:]
                else:
                    clean_text = clean_text[start_idx+7:].strip()
        
        # 2. Extração de JSON se presente (Prioridade máxima)
        json_match = re.search(r'[\[\{].*tool.*[\]\}]', clean_text, re.DOTALL)
        if json_match and not is_translation_pass:
            # Retorna apenas o JSON para o Dispatcher
            return clean_text[json_match.start():json_match.end()].strip()

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
            
            clean_answer = self._clean_response(answer)

            # Se for um JSON de ferramenta, pulamos a verificação de tradução e vamos direto pro dispatch
            has_json = "{" in clean_answer and ("tool" in clean_answer or "action" in clean_answer)
            
            if not has_json:
                # MECANISMO DE TRADUÇÃO PARA RESPOSTA DIRETA
                is_english = clean_answer.startswith("__NEED_TRANSLATION__") or (len(clean_answer) > 40 and not any(c in clean_answer for c in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ"))
                
                if is_english:
                    original_text = clean_answer.replace("__NEED_TRANSLATION__", "")
                    print(f"DEBUG: Texto em Inglês detectado. Traduzindo...")
                    translation_prompt = f"Traduza este texto para PORTUGUÊS (BRASIL). Responda APENAS a tradução direta, sem comentários: {original_text}"
                    translated = self.manager.generate_command(translation_prompt, system_context="SISTEMA_DE_TRADUCAO_PURAMENTE_EM_PORTUGUES_SEM_META_TALK")
                    clean_answer = self._clean_response(translated, is_translation_pass=True)

            if has_json:
                print(f"DEBUG: JSON detectado. Executando...")
                tool_result = ToolDispatcher.dispatch(clean_answer)
                
                # 2. Segunda Passada (Síntese) - Aqui usamos o histórico também
                synthesis_messages = full_messages.copy()
                synthesis_messages.append({"role": "assistant", "content": clean_answer})
                synthesis_messages.append({"role": "user", "content": f"Resultado das ferramentas: {tool_result}. Agora responda ao usuário de forma natural e amigável em Português (Brasil). NÃO responda com JSON nem com blocos de código ou raciocínio."})
                
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
