import json
import subprocess
import tempfile
import os
import sys
import re
from core.execution_service import ExecutionService
from core.tool_registry import tool_registry

# Importa todos os módulos de ferramentas para garantir o registro
import core.tools.system_tools
import core.tools.communication_tools
import core.tools.dev_tools
import core.tools.ai_tools
import core.tools.file_tools
import core.tools.productivity_tools

class ToolDispatcher:
    @staticmethod
    def dispatch(llm_response):
        """Analisa a resposta do LLM e executa ferramentas de forma extremamente robusta."""
        from main import MainApp
        main_app = MainApp.instance() if hasattr(MainApp, 'instance') else None
        
        # 1. Extração Agressiva de JSON
        data = ToolDispatcher._extract_json(llm_response)
        
        # 1b. Fallback: se nao tem JSON, tenta inferir da texto conversacional
        if not data:
            inferred = ToolDispatcher._infer_tool_from_text(llm_response)
            if inferred:
                data = inferred
        
        if not data:
            return ToolDispatcher._remove_think_tags(llm_response)
        
        if isinstance(data, dict):
            data = [data]
        
        results = []
        for item in data:
            if not isinstance(item, dict): continue
            
            # 2. Mapeamento Inteligente (Heurística de Ferramenta)
            tool_name = item.get("tool") or item.get("action")
            params = item.get("params") or {}
            
            # Se params vazio, tenta extrair do nivel superior
            if not params:
                known_params = ["app", "app_name", "path", "query", "command", "text", 
                               "content", "title", "body", "url", "link", "name", "skill",
                               "task", "pedido", "code", "args", "number", "pr", "repo",
                               "repository", "count", "duration", "priority", "status",
                               "prompt", "output", "filename", "old_string", "new_string",
                               "old", "new", "source", "dest", "dest_folder", "action",
                               "x", "y", "key", "level", "target", "message", "recipient",
                               "subject", "identifier", "tags", "due"]
                for kp in known_params:
                    if kp in item and kp != "tool" and kp != "action":
                        params[kp] = item[kp]
            
            # Se não tem tool_name mas tem chaves conhecidas, mapeia automaticamente
            if not tool_name:
                if "command" in item or "osascript" in str(item):
                    tool_name = "run_shell"
                    params = {"command": item.get("command") or item.get("osascript") or str(item)}
                elif "query" in item and len(item) == 1:
                    tool_name = "smart_search"
                    params = {"query": item.get("query")}
                elif "prompt" in item and "image" in str(item).lower():
                    tool_name = "generate_image"
                    params = {"prompt": item.get("prompt")}
            
            if not tool_name or tool_name == "none":
                continue

            print(f"Dispatcher: Executando {tool_name}({params})...")
            if main_app:
                main_app.hud.display_signal.emit(f"Executando {tool_name}...", "THINKING", 2000)
            
            # 3. Checagem de Segurança Ponderada
            from core.safety_service import SafetyService
            is_read_only = any(kw in str(params).lower() for kw in ["ls", "mdfind", "cat", "grep", "list", "get"])
            
            if SafetyService.is_critical(tool_name, params) and not is_read_only:
                print(f"Safety: Ação '{tool_name}' aguardando aprovação...")
                if not SafetyService.request_human_approval(tool_name, params):
                    results.append(f"Ação '{tool_name}' negada pelo usuário.")
                    continue

            # 4. Execução
            tool_func = tool_registry.get_tool(tool_name)
            if tool_func:
                try:
                    # Filtra params para aceitar apenas os que a função aceita
                    import inspect
                    sig = inspect.signature(tool_func)
                    valid_params = {k: v for k, v in params.items() if k in sig.parameters}
                    # Adiciona params None para os que faltam (com default)
                    for pname, param in sig.parameters.items():
                        if pname not in valid_params and param.default is not inspect.Parameter.empty:
                            valid_params[pname] = param.default
                    result = tool_func(**valid_params)
                    results.append(ToolDispatcher._format_result(tool_name, result))
                    if main_app and "Erro" not in str(result): main_app.sound.success()
                except Exception as tool_err:
                    results.append(f"Erro ao executar {tool_name}: {tool_err}")
            else:
                results.append(f"Ferramenta '{tool_name}' não encontrada.")
        
        return "\n".join(results)

    @staticmethod
    def _remove_think_tags(text):
        """Remove tags de pensamento para retorno limpo."""
        return re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()

    @staticmethod
    def _extract_json(text):
        """Extrai JSON de qualquer lugar da string, mesmo mal formatado."""
        try:
            # Prioridade para blocos de codigo markdown
            code_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            json_str = code_match.group(1) if code_match else text
            
            # Tenta encontrar o primeiro objeto JSON valido
            # Usa busca nao-greedy para evitar capturar texto demais
            start = json_str.find('{')
            if start == -1:
                start = json_str.find('[')
            if start == -1:
                return None
            
            # Conta chaves/colchetes para encontrar o fechamento correto
            depth = 0
            in_string = False
            escape = False
            end = -1
            opener = json_str[start]
            closer = '}' if opener == '{' else ']'
            
            for i in range(start, len(json_str)):
                c = json_str[i]
                if escape:
                    escape = False
                    continue
                if c == '\\' and in_string:
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == opener or (opener == '{' and c == '[') or (opener == '[' and c == '{'):
                    depth += 1
                elif c == closer or (closer == '}' and c == ']') or (closer == ']' and c == '}'):
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            if end > start:
                candidate = json_str[start:end]
                return json.loads(candidate)
        except:
            pass
        return None

    @staticmethod
    def _infer_tool_from_text(text):
        """Tenta inferir a ferramenta a partir de texto conversacional (fallback)."""
        clean = text.lower().strip()
        clean = re.sub(r'[^\w\s]', '', clean)
        
        # Sites conhecidos como URL (ANTES de app detection)
        known_sites = {"youtube": "https://youtube.com", "google": "https://google.com",
                       "github": "https://github.com", "twitter": "https://twitter.com",
                       "x": "https://x.com", "instagram": "https://instagram.com",
                       "facebook": "https://facebook.com", "linkedin": "https://linkedin.com"}
        for site, url in known_sites.items():
            if site in clean and ("abre" in clean or "abra" in clean or "abrir" in clean):
                return [{"tool": "open_url", "url": url}]
        
        # Padroes de URL explicita
        url_patterns = [
            r'(?:abre|abra|abra)\s+(?:o\s+)?(?:link|url|site|pagina|canal)\s+(.+)',
            r'(?:abre|abra|abra)\s+(?:o\s+)?(\w+\.\w+)',
        ]
        for pat in url_patterns:
            m = re.search(pat, clean)
            if m:
                url = m.group(1).strip()
                if not url.startswith("http"):
                    url = "https://" + url
                return [{"tool": "open_url", "url": url}]
        
        # Padroes de abertura de app
        open_patterns = [
            r'(?:abre|abra|abr[ir]|abrir)\s+(?:o\s+|a\s+|os\s+|as\s+)?(?:app\s+|aplicativo\s+)?(?:de\s+|do\s+|da\s+)?(\w+)(?:\s+para\s+.*?)?$',
            r'(?:abre|abra|abr[ir]|abrir)\s+(?:o\s+|a\s+)?(\w+)(?:\s+para\s+.*?)?$',
        ]
        for pat in open_patterns:
            m = re.search(pat, clean)
            if m:
                app_name = m.group(1).strip()
                if app_name in ["para", "mim", "por", "gentileza", "agora", "voce", "tu", "me", "te"]:
                    continue
                app_map = {"notas": "Notes", "notes": "Notes", "calendar": "Calendar", 
                          "calendario": "Calendar", "vscode": "Visual Studio Code",
                          "code": "Visual Studio Code", "cursor": "Cursor", "finder": "Finder"}
                resolved = app_map.get(app_name, app_name)
                return [{"tool": "open_app", "app": resolved}]
        
        # Padroes de criacao
        create_patterns = [
            r'(?:cria|criar|crie|nova?|novo)\s+(?:uma?\s+)?(?:nota|lembrete|evento|tarefa)\s*(.*)',
        ]
        for pat in create_patterns:
            m = re.search(pat, clean)
            if m:
                content = m.group(1).strip() if m.group(1) else ""
                if "nota" in clean:
                    return [{"tool": "create_note", "title": content or "Nova nota", "content": content}]
                elif "lembrete" in clean:
                    return [{"tool": "add_reminder", "title": content}]
                return [{"tool": "create_note", "title": content or "Nova nota", "content": content}]
        
        # Padroes de delecao
        delete_patterns = [
            r'(?:deleta|delete|exclu|apaga|remove)\s+(?:tod[oa]s?\s+)?(?:as?\s+)?(.+)',
        ]
        for pat in delete_patterns:
            m = re.search(pat, clean)
            if m:
                target = m.group(1).strip()
                if "nota" in target:
                    return [{"tool": "delete_all_notes"}]
                return None
        
        return None

    @staticmethod
    def _format_result(tool, result):
        """Formata o resultado para o LLM."""
        status = "SUCCESS"
        if isinstance(result, str) and ("Erro" in result or "falhou" in result or "não encontrei" in result.lower()):
            status = "FAILURE"
            
        output = str(result)
        if isinstance(result, dict):
            if "stdout" in result: output = result["stdout"].strip() or "Concluído."
            if "error" in result: output = f"Erro: {result['error']}"
        
        return f"[RESULTADO: {tool}] {status}\n{output}"
