import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class LinearService:
    def __init__(self):
        self.api_key = os.getenv("LINEAR_API_KEY")
        self.url = "https://api.linear.app/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key
        }

    def _query(self, query, variables=None):
        if not self.api_key: return {"error": "Linear API Key não configurada."}
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.url, 
                    json={"query": query, "variables": variables}, 
                    headers=self.headers,
                    timeout=15.0
                )
                return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_my_issues(self):
        """Busca as issues atribuídas ao usuário logado."""
        query = """
        query {
          viewer {
            assignedIssues(filter: { state: { type: { neq: "completed" } } }) {
              nodes {
                id
                identifier
                title
                priority
                state { name }
                cycle { name number }
              }
            }
          }
        }
        """
        res = self._query(query)
        if "error" in res: return res["error"]
        
        issues = res.get("data", {}).get("viewer", {}).get("assignedIssues", {}).get("nodes", [])
        if not issues: return "Nenhuma issue pendente no Linear."
        
        output = "Minhas Issues no Linear:\n"
        for issue in issues:
            cycle = f" (Ciclo {issue['cycle']['number']})" if issue.get('cycle') else ""
            output += f"- [{issue['identifier']}] {issue['title']} | Status: {issue['state']['name']}{cycle}\n"
        return output

    def get_completed_issues_today(self):
        """Busca as issues resolvidas hoje."""
        from datetime import datetime
        today_iso = datetime.utcnow().strftime("%Y-%m-%d")
        
        query = """
        query($filter: IssueFilter) {
          issues(filter: $filter) {
            nodes {
              identifier
              title
              completedAt
              state { name }
            }
          }
        }
        """
        # Filtra por issues completadas hoje
        variables = {
            "filter": {
                "completedAt": { "gt": today_iso },
                "state": { "type": { "eq": "completed" } }
            }
        }
        
        res = self._query(query, variables)
        if "error" in res: return res["error"]
        
        issues = res.get("data", {}).get("issues", {}).get("nodes", [])
        if not issues: return "Nenhuma issue concluída hoje."
        
        output = "Issues Concluídas Hoje:\n"
        for issue in issues:
            output += f"- [{issue['identifier']}] {issue['title']}\n"
        return output

    def get_cycle_summary(self):
        """Busca um resumo do ciclo atual (progresso)."""
        query = """
        query {
          cycles(filter: { isActive: { eq: true } }) {
            nodes {
              name
              number
              progress
              uncompletedIssuesCount
              completedIssuesCount
              issues {
                nodes {
                  identifier
                  title
                  state { name }
                }
              }
            }
          }
        }
        """
        res = self._query(query)
        if "error" in res: return res["error"]
        
        cycles = res.get("data", {}).get("cycles", {}).get("nodes", [])
        if not cycles: return "Nenhum ciclo ativo encontrado."
        
        cycle = cycles[0]
        progress = round(cycle['progress'] * 100, 1)
        output = f"Resumo do Ciclo {cycle['number']} ({cycle['name']}):\n"
        output += f"Progresso: {progress}% | {cycle['completedIssuesCount']} concluídas | {cycle['uncompletedIssuesCount']} pendentes\n"
        
        # Pega as últimas 3 concluídas para dar contexto
        completed = [i for i in cycle['issues']['nodes'] if i['state']['name'] in ['Done', 'Completed', 'Concluído']]
        if completed:
            output += "Últimas entregas do ciclo:\n"
            for issue in completed[:3]:
                output += f"- [{issue['identifier']}] {issue['title']}\n"
        
        return output
