from core.tool_registry import tool_registry
from core.execution_service import ExecutionService
from core.web_service import WebService
from core.memory_client import MemoryClient
from core.semantic_memory import SemanticMemory
import os

# Instâncias
memory = MemoryClient()

@tool_registry.register(name="smart_search", aliases=["find_anything", "procurar"])
def smart_search(query=None):
    if not query: return "O que você deseja que eu procure no seu Mac?"
    return ExecutionService.smart_search(query)

@tool_registry.register(name="open_app", aliases=["abrir"])
def open_app(app=None, app_name=None, path=None, folder=None):
    target_app = app or app_name or ""
    target_path = path or folder
    result = ExecutionService.open_app(target_app, target_path)
    
    # Self-healing logic
    if isinstance(result, dict) and result.get("error") and (target_path or target_app):
        retry_name = target_path or target_app
        new_path = ExecutionService.resolve_path(retry_name)
        if new_path:
            result = ExecutionService.open_app(target_app, new_path)
    return result

@tool_registry.register(name="open_url")
def open_url(url=None, link=None, browser=None):
    target_url = url or link or ""
    if not target_url: return "Faltou a URL."
    # Sempre usa o navegador padrão do sistema — ignora o parâmetro browser
    return ExecutionService.open_url(target_url, browser=None)

@tool_registry.register(name="memory_write", aliases=["save_fact"])
def memory_write(key=None, path=None, value=None, body=None):
    target_key = key or path or "fato_geral"
    target_value = value or body or ""
    
    memory.save_fact(target_key, target_value)
    SemanticMemory().write(target_key, target_value)
    return f"Fato memorizado com sucesso."

@tool_registry.register(name="memory_query", aliases=["search_memory"])
def memory_query(key=None, query=None):
    target_query = key or query or ""
    relevant = SemanticMemory().query(target_query)
    if relevant:
        return "Memórias encontradas:\n" + "\n".join(relevant)
    return memory.get_fact(target_query)

@tool_registry.register(name="create_note", aliases=["create_new_note", "nota", "criar_nota"])
def create_note(title=None, path=None, name=None, content=None, body=None):
    note_name = title or name or path or "Nota do Anders"
    # NÃO adiciona .txt — o app Notas do macOS cria notas HTML, não arquivos .txt
    note_content = content or body or ""
    if not note_content:
        return "Forneça o conteúdo da nota. Use: create_note(title='Título', content='Conteúdo aqui')"
    return ExecutionService.create_new_note(note_name, note_content)

@tool_registry.register(name="web_search")
def web_search(query=None):
    if not query: return "O que você quer pesquisar?"
    return WebService.search_and_summarize(query)

@tool_registry.register(name="list_files")
def list_files(path="."):
    return ExecutionService.list_files(path)

@tool_registry.register(name="read_file")
def read_file(path=""):
    return ExecutionService.read_file(path)

@tool_registry.register(name="get_system_info")
def get_system_info():
    return ExecutionService.get_system_info()

@tool_registry.register(name="run_python")
def run_python(code=None):
    if not code: return "Nenhum código fornecido."
    from core.sandbox_service import sandbox
    return sandbox.execute_python(code)
