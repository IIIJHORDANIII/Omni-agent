from core.tool_registry import tool_registry
from core.execution_service import ExecutionService
import os

@tool_registry.register(name="create_file", aliases=["criar_arquivo", "write_file"])
def create_file(path=None, content=None, filename=None, body=None):
    target_path = path or filename or ""
    target_content = content or body or ""
    if not target_path:
        return "Faltou o caminho do arquivo."
    return ExecutionService.create_file(target_path, target_content)

@tool_registry.register(name="replace_in_file", aliases=["editar_arquivo", "edit_file"])
def replace_in_file(path=None, old_string=None, new_string=None, old=None, new=None):
    target_path = path or ""
    target_old = old_string or old or ""
    target_new = new_string or new or ""
    if not target_path or not target_old:
        return "Faltou o caminho ou o texto original."
    return ExecutionService.replace_in_file(target_path, target_old, target_new)

@tool_registry.register(name="delete_file", aliases=["deletar_arquivo", "remover_arquivo"])
def delete_file(path=None, filename=None):
    import shutil
    target = path or filename or ""
    if not target:
        return "Faltou o caminho do arquivo."
    try:
        full_path = os.path.expanduser(target)
        if not os.path.exists(full_path):
            return f"Erro: Arquivo {target} não encontrado."
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return f"Arquivo {target} excluído com sucesso."
    except Exception as e:
        return f"Erro ao excluir arquivo: {e}"

@tool_registry.register(name="run_git", aliases=["git", "git_command"])
def run_git(args=None, command=None):
    target = args or command or "status"
    return ExecutionService.run_git(target)

@tool_registry.register(name="type_text", aliases=["digitar", "escrever"])
def type_text(text=None, content=None):
    target = text or content or ""
    if not target:
        return "Nenhum texto para digitar."
    return ExecutionService.type_text(target)

@tool_registry.register(name="finder_move", aliases=["mover_arquivo"])
def finder_move(source=None, dest=None, dest_folder=None):
    src = source or ""
    dst = dest or dest_folder or ""
    if not src or not dst:
        return "Faltou origem ou destino."
    return ExecutionService.finder_move_file(src, dst)

@tool_registry.register(name="finder_rename", aliases=["renomear_arquivo"])
def finder_rename(path=None, new_name=None):
    target = path or ""
    name = new_name or ""
    if not target or not name:
        return "Faltou caminho ou novo nome."
    return ExecutionService.finder_rename_file(target, name)

@tool_registry.register(name="generate_project", aliases=["criar_projeto"])
def generate_project(base_path=None, files_dict=None):
    if not base_path or not files_dict:
        return "Faltou caminho base ou dicionário de arquivos."
    return ExecutionService.generate_project(base_path, files_dict)
