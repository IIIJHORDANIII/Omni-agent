import re
from core.linear_service import LinearService
from core.github_service import GithubService
from core.memory_client import MemoryClient
from core.execution_service import ExecutionService


class ContextAggregator:
    def __init__(self):
        self.linear = LinearService()
        self.github = GithubService()
        self.memory = MemoryClient()

    def _fuzzy_match(self, needle, haystack, threshold=0.6):
        """Busca fuzzy: verifica se o nome do arquivo aparece como substring
        significativa, com tolerancia a variacoes."""
        needle_lower = needle.lower()
        haystack_lower = haystack.lower()

        # Match exato
        if needle_lower in haystack_lower:
            return True

        # Match por partes do nome (ex: "vision_service" em "src/core/vision_service.py")
        parts = needle_lower.replace('.py', '').replace('.js', '').replace('.ts', '').split('_')
        if len(parts) > 1:
            # Pelo menos metade das partes devem aparecer
            matches = sum(1 for p in parts if p and p in haystack_lower)
            if matches >= len(parts) * threshold:
                return True

        # Match por caminho relativo
        if '/' in needle_lower:
            path_part = needle_lower.split('/')[-1]
            if path_part in haystack_lower:
                return True

        return False

    def get_context_for_file(self, file_path):
        """Busca informacoes relevantes sobre o arquivo atual."""
        if not file_path or file_path == "unknown":
            return None

        filename = file_path.split("/")[-1]

        # 1. Busca no Linear
        linear_context = "Nenhuma issue vinculada"
        try:
            issues = self.linear.get_my_issues()
            if issues:
                for line in issues.split("\n"):
                    if self._fuzzy_match(filename, line):
                        linear_context = line.strip()
                        break
        except Exception:
            pass

        # 2. Busca no GitHub
        github_context = "Sem PRs ativos"
        try:
            activity = self.github.get_recent_activity()
            if activity:
                for line in activity.split("\n"):
                    if self._fuzzy_match(filename, line):
                        github_context = line.strip()
                        break
        except Exception:
            pass

        return {
            "file": filename,
            "linear": linear_context,
            "github": github_context
        }
