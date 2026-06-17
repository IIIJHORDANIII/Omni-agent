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
                    
                # Suporte a múltiplos formatos de JSON: 'tool', 'action' ou 'name' (OpenAI/Anthropic)
                tool_name = item.get("tool") or item.get("action") or item.get("name")
                
                # Suporte a parâmetros em 'params' ou 'arguments'
                params = item.get("params") or item.get("arguments")
                
                if params is None:
                    # Se não houver bloco específico, usa todos os outros campos como parâmetros
                    params = {k: v for k, v in item.items() if k not in ["tool", "action", "name", "params", "arguments", "message"]}
                
                # Se arguments for uma string (comum em alguns modelos), tenta converter para dict
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except:
                        pass

                if tool_name is None or tool_name == "none":
                    msg = item.get("message")
                    if msg: results.append(msg)
                    continue
                
                print(f"Dispatcher: Executando {tool_name} com params: {params}")
                if main_app:
                    main_app.hud.display_signal.emit(f"Executando {tool_name}...", "THINKING", 0)
                


                # Busca a ferramenta no registro
                tool_func = tool_registry.get_tool(tool_name)
                
                if tool_func:
                    try:
                        # Chama a ferramenta dinamicamente
                        result = tool_func(**params)
                        
                        # LÓGICA DE AUTO-CORREÇÃO (V1)
                        if isinstance(result, str) and ("Não encontrei" in result or "Erro" in result or "falhou" in result):
                            print(f"Dispatcher: Falha detectada em {tool_name}. Tentando estratégia alternativa...")
                            # Aqui poderíamos disparar uma nova chamada de LLM automaticamente.
                            # Por enquanto, formatamos o erro para que o LLM principal veja no próximo turno.
                        
                        results.append(ToolDispatcher._format_result(tool_name, result))
                        if main_app and "Erro" not in str(result): main_app.sound.success()
                    except Exception as tool_err:
                        results.append(f"Erro ao executar {tool_name}: {tool_err}")
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
