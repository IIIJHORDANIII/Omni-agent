import json
import subprocess
import tempfile
import os
import sys
from core.execution_service import ExecutionService
from core.memory_client import MemoryClient
from core.web_service import WebService
from core.github_service import GithubService
from core.linear_service import LinearService

# Instâncias globais
memory = MemoryClient()
github = GithubService()
linear = LinearService()

class ToolDispatcher:
    @staticmethod
    def dispatch(llm_response):
        """Analisa a resposta do LLM e executa uma lista de ferramentas com segurança."""
        # Sanitização: Remove qualquer resquício de tags de pensamento se elas vazarem
        sanitized_response = llm_response
        if "<think>" in llm_response:
            if "</think>" in llm_response:
                sanitized_response = llm_response.split("</think>")[-1]
            else:
                # Se a tag não fechou, ignora tudo antes do que parece ser o JSON
                start_json = llm_response.find('[')
                if start_json != -1:
                    sanitized_response = llm_response[start_json:]
                else:
                    return llm_response.strip()

        print(f"DEBUG: Resposta sanitizada: {sanitized_response}")
        
        try:
            # Tenta encontrar o início de um JSON (Array ou Objeto)
            start_arr = sanitized_response.find('[')
            start_obj = sanitized_response.find('{')
            
            if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
                start = start_arr
                end = sanitized_response.rfind(']') + 1
            elif start_obj != -1:
                start = start_obj
                end = sanitized_response.rfind('}') + 1
            else:
                return sanitized_response.strip()
                
            json_str = sanitized_response[start:end]
            # Validação extra: DeepSeek as vezes coloca JSON dentro de blocos de código
            if "```json" in sanitized_response:
                code_start = sanitized_response.find("```json") + 7
                code_end = sanitized_response.find("```", code_start)
                if code_end != -1:
                    json_str = sanitized_response[code_start:code_end].strip()

            data = json.loads(json_str)
            
            if isinstance(data, dict):
                data = [data]
            
            results = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                    
                # Robustez: aceita 'tool' ou 'action'
                tool = item.get("tool") or item.get("action")
                
                # Robustez: se não houver 'params', pega o que sobrar no objeto
                params = item.get("params")
                if params is None:
                    params = {k: v for k, v in item.items() if k not in ["tool", "action", "message"]}
                
                if tool is None or tool == "none":
                    msg = item.get("message")
                    if not msg or msg == "sua resposta":
                        # Se não há ferramenta nem mensagem, mas há texto fora do JSON, 
                        # ou se é apenas um objeto de "falha", retorna uma frase amigável.
                        return "Não entendi como ajudar com esse pedido específico."
                    results.append(msg)
                    continue
                
                print(f"DEBUG: Executando Tool: {tool} com params: {params}")
                
                result = None
                # Roteamento Inteligente
                if tool == "open_app":
                    result = ExecutionService.open_app(params.get("app") or params.get("app_name") or "")
                elif tool == "control_app":
                    result = ExecutionService.control_app_ui(
                        params.get("app") or params.get("app_name"),
                        params.get("action") or params.get("script")
                    )
                elif tool == "open_url":

                    url = params.get("url") or params.get("link") or ""
                    if url:
                        result = ExecutionService.open_url(url)
                    else:
                        result = "Faltou me dizer qual site abrir."
                elif tool == "describe_screen" or tool == "analyze_screen":
                    # Usa o VisionService real em vez do Swift nativo
                    from core.vision_service import VisionService
                    vision = VisionService()
                    result = vision.describe_screen()
                elif tool == "run_protocol":
                    from core.protocol_manager import ProtocolManager
                    from core.llm_manager import LLMManager
                    llm = LLMManager()
                    result = ProtocolManager.run_protocol(params.get("name"), llm_manager=llm)
                elif tool == "create_tool" or tool == "genesis_tool":
                    from core.tool_generator import ToolGenerator
                    from core.llm_manager import LLMManager
                    llm = LLMManager()
                    result = ToolGenerator.generate_and_execute(llm, params.get("requirement") or params.get("task", ""))
                elif tool == "set_volume":
                    level = params.get("level") or params.get("volume", 50)
                    result = ExecutionService.set_system_volume(level)
                elif tool == "set_brightness":
                    level = params.get("level") or params.get("brightness", 50)
                    result = ExecutionService.manage_hardware("set_brightness", level)
                elif tool == "run_python":
                    code = params.get("code") or ""
                    result = ToolDispatcher._execute_python_sandbox(code)
                elif tool == "run_shell":
                    command = params.get("command") or ""
                    result = ExecutionService.run_terminal_command(command)
                elif tool == "list_files":
                    dir_path = params.get("path") or "."
                    result = ExecutionService.list_files(dir_path)
                elif tool == "read_file":
                    file_path = params.get("path") or ""
                    result = ExecutionService.read_file(file_path)
                elif tool == "generate_project":
                    result = ExecutionService.generate_project(
                        params.get("path") or params.get("base_path", "novo_projeto"),
                        params.get("files") or params.get("files_dict", {})
                    )
                elif tool == "web_search":
                    query = params.get("query") or ""
                    result = WebService.search_and_summarize(query)
                elif tool == "web_read":
                    url = params.get("url") or ""
                    result = WebService.get_page_content(url)
                elif tool == "search_files":
                    pattern = params.get("pattern") or ""
                    path = params.get("path") or "."
                    cmd = f"grep -rnw '{path}' -e '{pattern}' | head -n 20"
                    result = ExecutionService.run_terminal_command(cmd)
                elif tool == "memory_write":
                    # Salva fatos na memória persistente
                    key = params.get("key") or params.get("path") or "fato_geral"
                    value = params.get("value") or params.get("body") or ""
                    result = memory.save_fact(key, value)
                elif tool == "memory_query":
                    # Busca na memória
                    key = params.get("key") or params.get("query") or ""
                    result = memory.get_fact(key)
                elif tool == "mail_draft":
                    result = ExecutionService.mail_create_draft(
                        params.get("subject", "Sem Assunto"),
                        params.get("body", ""),
                        params.get("recipient", "")
                    )
                elif tool == "mail_list":
                    result = ExecutionService.get_latest_emails(params.get("count", 5))
                elif tool == "mail_unread":
                    result = ExecutionService.mail_unread(params.get("count", 10))
                elif tool == "mail_search":
                    result = ExecutionService.mail_search(params.get("query", ""))
                elif tool == "notes_search":
                    result = ExecutionService.notes_search(params.get("query", ""))
                elif tool == "create_note" or tool == "create_new_note":
                    # Aceita tanto 'path'/'name' quanto 'title' para o nome da nota
                    note_name = params.get("path") or params.get("name") or params.get("title") or "Nota sem título.txt"
                    # Garante extensão .txt se não houver
                    if not note_name.endswith(".txt") and not "." in note_name:
                        note_name += ".txt"
                    result = ExecutionService.create_new_note(note_name, params.get("content") or params.get("body", ""))
                elif tool == "clear_notes":
                    result = ExecutionService.clear_notes()
                elif tool == "finder_move":
                    result = ExecutionService.finder_move_file(params.get("source"), params.get("dest"))
                elif tool == "finder_rename":
                    result = ExecutionService.finder_rename_file(params.get("path"), params.get("name"))
                elif tool == "get_system_info":
                    result = ExecutionService.get_system_info()
                elif tool == "run_tests":
                    result = ExecutionService.run_tests(params.get("path") or ".")
                elif tool == "github_list_prs":
                    result = github.get_pull_requests(params.get("repo") or params.get("repository", ""))
                elif tool == "github_pr_details":
                    result = github.get_pr_details(params.get("repo") or params.get("repository", ""), params.get("pr") or params.get("number", 0))
                elif tool == "github_commits":
                    result = github.get_recent_commits(params.get("repo") or params.get("repository", ""), params.get("count", 5))
                elif tool == "linear_my_issues":
                    result = linear.get_my_issues()
                elif tool == "linear_cycle":
                    result = linear.get_cycle_summary()
                elif tool == "project_summary":
                    result = ExecutionService.get_project_summary(params.get("path") or ".")
                elif tool == "find_project":
                    result = ExecutionService.find_project(params.get("name") or params.get("query", ""))
                elif tool == "get_calendar_events":
                    result = ExecutionService.get_calendar_events()
                elif tool == "get_reminders":
                    result = ExecutionService.get_reminders()
                elif tool == "add_reminder":
                    result = ExecutionService.add_reminder(params.get("title") or params.get("name", ""))
                elif tool in ["move_window", "bring_to_front", "close_app", "click_at", "toggle_mute", "type_text", "press_key", "scroll"]:
                    # Delegar para Swift (Native Bridge)
                    swift_command = {"action": tool, **params}
                    result = ExecutionService.send_command_to_swift(swift_command)
                else:
                    if hasattr(ExecutionService, tool):
                        method = getattr(ExecutionService, tool)
                        result = method(**params)
                    else:
                        result = f"Ferramenta {tool} não encontrada."

                # Formatação Amigável do Resultado
                if isinstance(result, dict):
                    if tool in ["describe_screen", "analyze_screen"] or result.get("action") == "analyze_screen":
                        text = result.get("analysis") or result.get("text", "")
                        if text:
                            results.append(f"Na sua tela eu vejo: {text[:200]}...")
                        else:
                            results.append("Não consegui identificar nada na tela agora.")
                    elif result.get("status") == "error":
                        results.append(f"Erro ao executar {tool}.")
                    elif "stdout" in result:
                        # Se for uma ferramenta de leitura (e-mail, calendário), mostra o conteúdo
                        content = result["stdout"].strip()
                        if content:
                            results.append(content)
                        else:
                            results.append("Concluído (sem detalhes).")
                    elif result.get("status") == "queued":
                        results.append(f"Pronto.")
                    else:
                        results.append("Concluído.")
                else:
                    if tool == "open_url" and "http" in str(result):
                        results.append("Abrindo site.")
                    else:
                        results.append(str(result))
            
            return "\n".join(results)
            
        except Exception as e:
            return f"Erro ao processar comando: {e}"

    @staticmethod
    def _execute_python_sandbox(code):
        """Executa um script Python de forma isolada e retorna o output."""
        if not code: return "Nenhum código fornecido."
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
                tmp.write(code.encode())
                tmp_path = tmp.name
            
            # Executa com o mesmo venv
            result = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=10)
            os.remove(tmp_path)
            
            if result.returncode == 0:
                return f"Código executado: {result.stdout.strip()}"
            else:
                return f"Erro no código: {result.stderr.strip()}"
        except Exception as e:
            return f"Falha no sandbox: {e}"
