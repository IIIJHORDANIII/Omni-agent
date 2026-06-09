from core.linear_service import LinearService
from core.github_service import GithubService
from core.memory_client import MemoryClient
from core.execution_service import ExecutionService

class ContextAggregator:
    def __init__(self):
        self.linear = LinearService()
        self.github = GithubService()
        self.memory = MemoryClient()

    def get_context_for_file(self, file_path):
        """Busca informações relevantes sobre o arquivo atual."""
        if not file_path or file_path == "unknown":
            return None
            
        filename = file_path.split("/")[-1]
        
        # 1. Busca no Linear (Simplificado: vê se o nome do arquivo aparece em alguma issue aberta)
        # Em um cenário real, poderíamos usar busca semântica ou regex em branch names
        linear_context = "Nenhuma issue vinculada"
        try:
            issues = self.linear.get_my_issues()
            if filename.lower() in issues.lower():
                # Extrai a linha que contém o nome do arquivo
                for line in issues.split("\n"):
                    if filename.lower() in line.lower():
                        linear_context = line.strip()
                        break
        except: pass

        # 2. Busca no GitHub (Vê se há PRs abertos mencionando o arquivo)
        # Por simplicidade, vamos pegar a atividade recente de PRs
        github_context = "Sem PRs ativos"
        try:
            activity = self.github.get_recent_activity()
            if filename.lower() in activity.lower():
                for line in activity.split("\n"):
                    if filename.lower() in line.lower():
                        github_context = line.strip()
                        break
        except: pass

        return {
            "file": filename,
            "linear": linear_context,
            "github": github_context
        }
