from core.tool_registry import tool_registry
from core.execution_service import ExecutionService

try:
    from core.github_service import GithubService
    github = GithubService()
except ImportError:
    github = None

try:
    from core.linear_service import LinearService
    linear = LinearService()
except ImportError:
    linear = None

@tool_registry.register(name="github_list_prs")
def github_list_prs(repo="", repository=""):
    if not github: return "GitHub nao disponivel (PyGithub nao instalado)."
    return github.get_pull_requests(repo or repository)

@tool_registry.register(name="github_pr_details")
def github_pr_details(repo="", repository="", pr=0, number=0):
    if not github: return "GitHub nao disponivel (PyGithub nao instalado)."
    return github.get_pr_details(repo or repository, pr or number)

@tool_registry.register(name="github_commits")
def github_commits(repo="", repository="", count=5):
    if not github: return "GitHub nao disponivel (PyGithub nao instalado)."
    return github.get_recent_commits(repo or repository, count)

@tool_registry.register(name="linear_my_issues")
def linear_my_issues():
    if not linear: return "Linear nao disponivel."
    return linear.get_my_issues()

@tool_registry.register(name="run_tests")
def run_tests(path="."):
    return ExecutionService.run_tests(path)

@tool_registry.register(name="project_summary")
def project_summary(path="."):
    return ExecutionService.get_project_summary(path)

@tool_registry.register(name="auto_github_pr")
def auto_github_pr(repo_name=None, title=None, body=None):
    """
    Detecta o contexto git local e cria um PR automaticamente.
    Se repo_name for vago, tenta descobrir via terminal.
    """
    try:
        # 1. Tenta descobrir o repo e branch atual via shell
        repo_info = ExecutionService.run_terminal_command("git remote get-url origin && git rev-parse --abbrev-ref HEAD")
        if "error" in repo_info or not repo_info.get("stdout"):
            return "Não consegui detectar um repositório Git nesta pasta. Certifique-se de estar na raiz do projeto."
        
        lines = repo_info["stdout"].strip().split("\n")
        remote_url = lines[0]
        current_branch = lines[1]
        
        # Extrai nome do repo da URL (ex: https://github.com/user/repo.git -> user/repo)
        import re
        match = re.search(r'github\.com[:/](.*)\.git', remote_url)
        full_repo = match.group(1) if match else repo_name
        
        if not full_repo:
            return "Não consegui identificar o nome do repositório no GitHub."

        # 2. Cria o PR
        from core.github_service import GithubService
        gh = GithubService()
        result = gh.create_pull_request(
            repo=full_repo,
            title=title or f"Update from {current_branch}",
            head=current_branch,
            base="main",
            body=body or "Pull request gerado automaticamente pelo Anders Agent."
        )
        return f"PR Criado com sucesso no repositório {full_repo}!\nResultado: {result}"
    except Exception as e:
        return f"Erro ao automatizar PR: {e}"

@tool_registry.register(name="vscode_sync")
def vscode_vscode_sync():
    """Tenta ler o que está aberto no VS Code agora (via AppleScript)."""
    script = '''
    tell application "Visual Studio Code"
        return {name of front window, POSIX path of (file of active document of front window as alias)}
    end tell
    '''
    return ExecutionService.run_applescript(script)

@tool_registry.register(name="run_shell", aliases=["terminal", "cmd"])
def run_shell(command=""):
    """Executa um comando no shell persistente (preserva diretório e estado)."""
    if not command: return "Nenhum comando fornecido."
    from core.persistent_shell import shell
    return shell.execute(command)
