import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

class GithubService:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.client = Github(self.token) if self.token else None

    def get_pull_requests(self, repo_name):
        """Lista PRs abertos em um repositório."""
        if not self.client: return "GitHub Token não configurado."
        try:
            repo = self.client.get_repo(repo_name)
            pulls = repo.get_pulls(state='open')
            results = []
            for pr in pulls[:5]:
                results.append(f"PR #{pr.number}: {pr.title} (por {pr.user.login})")
            return "\n".join(results) if results else "Nenhum PR aberto."
        except Exception as e:
            return f"Erro ao acessar GitHub: {e}"

    def get_pr_details(self, repo_name, pr_number):
        """Obtém detalhes e diff de um PR específico."""
        if not self.client: return "GitHub Token não configurado."
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(int(pr_number))
            # Pega os primeiros 5 arquivos do diff para não estourar contexto
            files = pr.get_files()
            diff_summary = ""
            for f in list(files)[:3]:
                diff_summary += f"\nArquivo: {f.filename}\nPatch: {f.patch[:1000]}...\n"
            
            return f"Título: {pr.title}\nDescrição: {pr.body}\nDiff Resumido: {diff_summary}"
        except Exception as e:
            return f"Erro ao obter detalhes do PR: {e}"

    def get_recent_commits(self, repo_name, count=5):
        """Lista os últimos commits em um repositório."""
        if not self.client: return "GitHub Token não configurado."
        try:
            repo = self.client.get_repo(repo_name)
            commits = repo.get_commits()
            results = []
            for commit in commits[:count]:
                results.append(f"- {commit.commit.message} (por {commit.commit.author.name})")
            return f"Últimos commits em {repo_name}:\n" + "\n".join(results)
        except Exception as e:
            return f"Erro ao acessar commits no GitHub: {e}"

    def get_recent_activity(self):
        """Busca PRs abertos ou atualizados recentemente em todos os repositórios monitorados."""
        if not self.client: return "GitHub Token não configurado."
        try:
            # Pega eventos do usuário (atividades recentes)
            user = self.client.get_user()
            events = user.get_events()
            pull_requests = []
            
            # Filtra os últimos 20 eventos por PullRequestEvent
            for event in list(events)[:20]:
                if event.type == "PullRequestEvent":
                    pr = event.payload['pull_request']
                    pull_requests.append(f"- [{pr['base']['repo']['name']}] PR #{pr['number']}: {pr['title']} ({pr['state']})")
            
            if not pull_requests: return "Nenhuma atividade de PR detectada recentemente."
            return "Atividade Recente no GitHub:\n" + "\n".join(list(set(pull_requests))[:5])
        except Exception as e:
            return f"Erro ao buscar atividade do GitHub: {e}"

    def create_pull_request(self, repo_name, title, head, base="main", body=""):
        """Cria um Pull Request em um repositório."""
        if not self.client: return "GitHub Token não configurado."
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.create_pull(title=title, body=body, head=head, base=base)
            return f"Pull Request criado com sucesso: {pr.html_url}"
        except Exception as e:
            return f"Erro ao criar Pull Request: {e}"
