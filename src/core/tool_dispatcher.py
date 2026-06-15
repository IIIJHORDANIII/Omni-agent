import json
import subprocess
import tempfile
import os
import sys
from core.execution_service import ExecutionService
from core.tool_registry import tool_registry

# Importa todos os módulos de ferramentas para garantir o registro
import core.tools.system_tools
import core.tools.communication_tools
import core.tools.dev_tools
import core.tools.ai_tools

class ToolDispatcher:
    @staticmethod
    def dispatch(llm_response):
        """Analisa a resposta do LLM e executa ferramentas registradas dinamicamente."""
        from main import MainApp
        main_app = MainApp.instance() if hasattr(MainApp, 'instance') else None
        
        sanitized_response = ToolDispatcher._sanitize(llm_response)
        
        try:
            data = ToolDispatcher._extract_json(sanitized_response)
            if not data:
                return sanitized_response.strip()
            
            if isinstance(data, dict):
                data = [data]
            
            results = []
            for item in data:
                if not isinstance(item, dict): continue
                    
                tool_name = item.get("tool") or item.get("action")
                params = item.get("params")
                if params is None:
                    params = {k: v for k, v in item.items() if k not in ["tool", "action", "message"]}
                
                if tool_name is None or tool_name == "none":
                    msg = item.get("message")
                    if msg: results.append(msg)
                    continue
                
                print(f"Dispatcher: Executando {tool_name} com params: {params}")
                if main_app:
                    main_app.hud.display_signal.emit(f"Executando {tool_name}...", "THINKING", 0)
                
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
                elif tool in ["mail_search", "search_emails", "buscar_emails"]:
                    result = ExecutionService.mail_search(params.get("query") or params.get("termo") or "")
                elif tool in ["mail_unread", "unread_emails", "emails_nao_lidos"]:
                    result = ExecutionService.mail_unread(params.get("count", 10))
                elif tool == "mail_list":
                    result = ExecutionService.get_latest_emails(params.get("count", 5))
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
                elif tool == "github_create_pr":
                    result = github.create_pull_request(
                        params.get("repo") or params.get("repository", ""),
                        params.get("title", "Update from Omni-agent"),
                        params.get("head"),
                        params.get("base", "main"),
                        params.get("body", "")
                    )
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
                elif tool == "toggle_mute":
                    # Delegar para Swift (Native Bridge)
                    swift_command = {"action": tool, **params}
                    result = ExecutionService.send_command_to_swift(swift_command)
                elif tool == "run_shortcut":
                    result = ExecutionService.run_shortcut(params.get("name"), params.get("input", ""))
                elif tool == "list_shortcuts":
                    result = ExecutionService.list_shortcuts()
                elif tool == "set_focus":
                    result = ExecutionService.set_focus_mode(params.get("mode", "Não Perturbe"))
                elif tool == "screenshot":
                    result = ExecutionService.capture_screen(params.get("path"))
                elif tool == "download_file":
                    result = ExecutionService.download_file(params.get("url"), params.get("path"))
                elif tool == "media_cut":
                    from core.media_editor import MediaEditor
                    result = MediaEditor.cut_video(params.get("input"), params.get("start"), params.get("duration"), params.get("output"))
                elif tool == "media_to_mp3":
                    from core.media_editor import MediaEditor
                    result = MediaEditor.convert_to_mp3(params.get("input"), params.get("output"))
                elif tool == "generate_image":
                    from core.image_generator import ImageGenerator
                    result = ImageGenerator.generate_image(params.get("prompt"), params.get("output"))
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
                    results.append(f"Ferramenta '{tool_name}' não encontrada.")
            
            return "\n".join(results)
            
        except Exception as e:
            return f"Erro ao processar comando: {e}"

    @staticmethod
    def _sanitize(text):
        if "<think>" in text:
            if "</think>" in text:
                return text.split("</think>")[-1]
            start_json = text.find('[')
            if start_json != -1: return text[start_json:]
        return text

    @staticmethod
    def _extract_json(text):
        try:
            import re
            # Prioridade para blocos de código JSON
            code_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if code_match:
                return json.loads(code_match.group(1))
            
            # Busca por colchetes ou chaves
            start_arr = text.find('[')
            start_obj = text.find('{')
            
            if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
                start, end = start_arr, text.rfind(']') + 1
            elif start_obj != -1:
                start, end = start_obj, text.rfind('}') + 1
            else:
                return None
                
            return json.loads(text[start:end])
        except:
            return None

    @staticmethod
    def _format_result(tool, result):
        """Formata o resultado para o LLM, incluindo metadados de execução."""
        status = "SUCCESS"
        if isinstance(result, str) and ("Erro" in result or "falhou" in result or "não encontrei" in result.lower()):
            status = "FAILURE"
        elif isinstance(result, dict) and result.get("returncode", 0) != 0:
            status = "FAILURE"
            
        output = str(result)
        if isinstance(result, dict):
            if "stdout" in result: output = result["stdout"].strip() or "Concluído."
            if "error" in result: output = f"Erro: {result['error']}"
        
        return f"[OBSERVATION: {tool}] status: {status}\noutput: {output}"
