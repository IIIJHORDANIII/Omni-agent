import time
from core.vision_service import VisionService
from core.execution_service import ExecutionService

class WebService:
    """
    Protocolo Holograma: Navegação Web guiada por Visão.
    """
    def __init__(self, llm_manager, vision=None):
        self.llm = llm_manager
        self.vision = vision if vision else VisionService()

    def navigate_to(self, url):
        ExecutionService.open_url(url)
        time.sleep(3) # Espera carregar

    @staticmethod
    def search_and_summarize(query):
        """Busca no DuckDuckGo e retorna um resumo dos resultados."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results: return "Nenhum resultado encontrado."
                
                output = f"Resultados para '{query}':\n"
                for r in results:
                    output += f"- {r['title']}: {r['href']}\n  {r['body'][:200]}...\n\n"
                return output
        except Exception as e:
            return f"Erro na busca web: {e}"

    @staticmethod
    def get_page_content(url):
        """Lê o conteúdo de uma página web (texto puro)."""
        import httpx
        try:
            with httpx.Client(follow_redirects=True) as client:
                response = client.get(url, timeout=10.0)
                # Tenta remover HTML simples se não houver um parser robusto
                import re
                text = re.sub(r'<[^>]+>', '', response.text)
                # Limpa espaços excessivos
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:2000] # Limite para não estourar contexto
        except Exception as e:
            return f"Erro ao ler página: {e}"
