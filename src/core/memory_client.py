import os
from datetime import datetime

class MemoryClient:
    """
    Cliente de Memória integrado com o ecossistema ai-memory (MCP).
    """
    def __init__(self):
        pass

    def save_fact(self, key, value):
        """Salva um fato durável na memória semântica local (ChromaDB)."""
        try:
            from core.semantic_memory import SemanticMemory
            return SemanticMemory().write(key, value)
        except Exception as e:
            return f"Erro ao memorizar fato: {e}"

    def get_fact(self, query, exact_only=False):
        """Consulta a memória semântica. Tenta busca exata, depois vetorial."""
        try:
            from core.semantic_memory import SemanticMemory
            sm = SemanticMemory()
            exact = sm.get_exact_fact(query)
            if exact: return exact
            if exact_only: return None
            results = sm.query(query, n_results=1)
            if results:
                return results[0]
            return None
        except Exception as e:
            return None

    def get_all_memory(self):
        return "Conectado ao ecossistema ai-memory (MCP)."

    def store_observation(self, text):
        """Armazena uma observação temporal na memória."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.save_fact(f"Atividade_{today}", text)
