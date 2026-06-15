import os
import time
from core.semantic_memory import SemanticMemory

class ErrorLearningService:
    """
    Sistema de Memória Viva que aprende com falhas do sistema e do próprio agente.
    """
    def __init__(self):
        self.semantic_memory = SemanticMemory()

    def learn_from_error(self, command, error_msg, solution_suggestion):
        """Memoriza um erro e sua correção sugerida."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cmd_name = command.split()[0] if command else "unknown"
        memory_key = f"erro_resolvido_{cmd_name}_{int(time.time())}"
        
        knowledge = (
            f"[CONHECIMENTO DE ERRO - {timestamp}]\n"
            f"COMANDO: {command}\n"
            f"ERRO: {error_msg}\n"
            f"SOLUÇÃO/CORREÇÃO: {solution_suggestion}"
        )
        
        self.semantic_memory.write(memory_key, knowledge)
        print(f"ErrorLearning: Conhecimento sobre '{cmd_name}' memorizado.")

    def check_for_prior_errors(self, command):
        """Consulta se já houve erros similares no passado para prevenir repetição."""
        query = f"erro no comando {command}"
        memories = self.semantic_memory.query(query)
        if memories:
            return memories[0] # Retorna a correção mais relevante
        return None

# Instância global
error_learner = ErrorLearningService()
