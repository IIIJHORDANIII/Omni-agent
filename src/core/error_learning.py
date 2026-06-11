import os
import time
from core.semantic_memory import SemanticMemory
from core.llm_manager import LLMManager

class ErrorLearningService:
    """
    Sistema de Memória Viva que aprende com falhas do sistema e do próprio agente.
    """
    def __init__(self):
        self.semantic_memory = SemanticMemory()
        self.llm = LLMManager()

    def learn_from_error(self, command, error_msg, solution_suggestion):
        """Memoriza um erro e sua correção sugerida."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        memory_key = f"error_learning_{int(time.time())}"
        
        # Formata o conhecimento para a memória semântica
        knowledge = f"""
        [CONHECIMENTO DE ERRO - {timestamp}]
        COMANDO: {command}
        ERRO: {error_msg}
        SOLUÇÃO/CORREÇÃO: {solution_suggestion}
        """
        
        # Salva na memória semântica para RAG futuro
        self.semantic_memory.write(f"erro_resolvido_{command.split()[0]}", knowledge)
        print(f"ErrorLearning: Conhecimento sobre '{command.split()[0]}' memorizado.")

    def check_for_prior_errors(self, command):
        """Consulta se já houve erros similares no passado para prevenir repetição."""
        query = f"erro no comando {command}"
        memories = self.semantic_memory.query(query)
        if memories:
            return memories[0] # Retorna a correção mais relevante
        return None

# Instância global
error_learner = ErrorLearningService()
