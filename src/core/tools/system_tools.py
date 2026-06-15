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
    return ExecutionService.open_url(target_url, browser=browser)

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

@tool_registry.register(name="create_note", aliases=["create_new_note"])
def create_note(title=None, content=None, body=None):
    note_name = title or "Nota sem título"
    note_content = content or body or ""
    return ExecutionService.create_new_note(note_name, note_content)

@tool_registry.register(name="delete_all_notes", aliases=["limpar_notas"])
def delete_all_notes():
    """Apaga todas as notas do aplicativo Notas nativo do macOS."""
    return ExecutionService.clear_notes()

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

# --- FERRAMENTAS UNIVERSAIS PARA APPS macOS ---

@tool_registry.register(name="app_action", aliases=["app_script", "executar_apple"])
def app_action(app=None, action=None, script=None):
    """Executa uma ação AppleScript em qualquer app do macOS.
    Exemplos: app_action(app="Notes", action="create"), app_action(app="Calendar", script="tell application \"Calendar\" to activate")
    """
    target_app = app or ""
    action_type = action or ""
    custom_script = script or ""
    
    if custom_script:
        return ExecutionService.run_applescript(custom_script)
    
    if not target_app:
        return "Faltou o nome do app."
    
    safe_app = target_app.replace('"', '\\"')
    
    actions = {
        "activate": f'tell application "{safe_app}" to activate',
        "create": f'tell application "{safe_app}" to activate',
        "quit": f'tell application "{safe_app}" to quit',
        "close": f'tell application "{safe_app}" to quit',
        "list": f'tell application "System Events" to get name of every window of process "{safe_app}"',
        "minimize": f'tell application "System Events" to set minimized of window 1 of process "{safe_app}" to true',
        "maximize": f'tell application "System Events" to set position of window 1 of process "{safe_app}" to {0, 0}',
    }
    
    as_script = actions.get(action_type, f'tell application "{safe_app}" to activate')
    return ExecutionService.run_applescript(as_script)

@tool_registry.register(name="app_create")
def app_create(app=None, type=None, title=None, content=None, body=None):
    """Cria um item novo em qualquer app. Funciona com Notes, Calendar, Reminders, Mail, etc."""
    target_app = app or ""
    item_type = type or "note"
    item_title = title or ""
    item_content = content or body or ""
    
    if not target_app:
        return "Faltou o nome do app."
    
    safe_app = target_app.replace('"', '\\"')
    safe_title = item_title.replace('"', '\\"')
    safe_content = item_content.replace('"', '\\"')
    
    # Mapeia apps para acoes
    app_lower = target_app.lower()
    
    if "note" in app_lower:
        script = f'''
        tell application "{safe_app}"
            activate
            make new note at folder "Notes" with properties {{name:"{safe_title}", body:"{safe_content}"}}
        end tell
        '''
    elif "calendar" in app_lower:
        script = f'''
        tell application "{safe_app}"
            activate
            tell calendar "Home"
                make new event with properties {{summary:"{safe_title}", description:"{safe_content}"}}
            end tell
        end tell
        '''
    elif "reminder" in app_lower:
        script = f'''
        tell application "{safe_app}"
            activate
            make new reminder with properties {{name:"{safe_title}", body:"{safe_content}"}}
        end tell
        '''
    elif "mail" in app_lower:
        script = f'''
        tell application "{safe_app}"
            activate
            set newMessage to make new outgoing message with properties {{subject:"{safe_title}", content:"{safe_content}", visible:true}}
        end tell
        '''
    else:
        # Generic: tenta ativar o app
        script = f'tell application "{safe_app}" to activate'
    
    return ExecutionService.run_applescript(script)

@tool_registry.register(name="app_edit")
def app_edit(app=None, target=None, field=None, new_value=None):
    """Edita um item existente em qualquer app."""
    target_app = app or ""
    target_item = target or ""
    edit_field = field or "body"
    value = new_value or ""
    
    if not target_app:
        return "Faltou o nome do app."
    
    safe_app = target_app.replace('"', '\\"')
    safe_target = target_item.replace('"', '\\"')
    safe_value = value.replace('"', '\\"')
    safe_field = edit_field.replace('"', '\\"')
    
    script = f'''
    tell application "{safe_app}"
        activate
        set theItem to {safe_field} of {safe_target}
        set {safe_field} of {safe_target} to "{safe_value}"
    end tell
    '''
    return ExecutionService.run_applescript(script)

@tool_registry.register(name="app_delete")
def app_delete(app=None, target=None, confirm=None):
    """Deleta um item de qualquer app."""
    target_app = app or ""
    target_item = target or ""
    
    if not target_app:
        return "Faltou o nome do app."
    
    safe_app = target_app.replace('"', '\\"')
    safe_target = target_item.replace('"', '\\"')
    
    app_lower = target_app.lower()
    
    if "note" in app_lower:
        script = f'''
        tell application "{safe_app}"
            activate
            delete note "{safe_target}" of folder "Notes"
        end tell
        '''
    elif "reminder" in app_lower:
        script = f'''
        tell application "{safe_app}"
            activate
            delete reminder "{safe_target}" of list "Reminders"
        end tell
        '''
    else:
        script = f'''
        tell application "System Events"
            tell process "{safe_app}"
                set frontmost to true
            end tell
        end tell
        '''
    
    return ExecutionService.run_applescript(script)

@tool_registry.register(name="app_list")
def app_list(app=None, what=None):
    """Lista itens de qualquer app (notas, eventos, lembretes, janelas, etc.)."""
    target_app = app or ""
    list_what = what or "items"
    
    if not target_app:
        return "Faltou o nome do app."
    
    safe_app = target_app.replace('"', '\\"')
    
    app_lower = target_app.lower()
    what_lower = list_what.lower()
    
    if "note" in app_lower:
        script = f'''
        tell application "{safe_app}"
            set noteList to ""
            repeat with n in notes
                set noteList to noteList & (name of n) & "\\n"
            end repeat
            return noteList
        end tell
        '''
    elif "calendar" in app_lower:
        script = f'''
        tell application "{safe_app}"
            set eventList to ""
            repeat with e in (current calendar)'s events
                set eventList to eventList & (summary of e) & "\\n"
            end repeat
            return eventList
        end tell
        '''
    elif "reminder" in app_lower:
        script = f'''
        tell application "{safe_app}"
            set remList to ""
            repeat with r in reminders
                set remList to remList & (name of r) & "\\n"
            end repeat
            return remList
        end tell
        '''
    else:
        script = f'''
        tell application "System Events"
            get name of every window of process "{safe_app}"
        end tell
        '''
    
    result = ExecutionService.run_applescript(script)
    return result if result else f"Nenhum item encontrado em {target_app}."
