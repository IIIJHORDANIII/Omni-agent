import json
import os
import time

class SessionPersistence:
    """
    Garante a continuidade da sessão salvando o estado do Agente.
    Permite retomar conversas e tarefas após reinicialização.
    """
    def __init__(self, persistence_file="memory_db/session_state.json"):
        self.persistence_file = persistence_file
        self.state = {
            "last_active": 0,
            "messages": [],
            "active_tasks": [],
            "current_skill": None
        }
        self.load()

    def save(self, messages=None, active_tasks=None, current_skill=None):
        """Salva o estado atual."""
        self.state["last_active"] = time.time()
        if messages is not None: self.state["messages"] = messages
        if active_tasks is not None: self.state["active_tasks"] = active_tasks
        if current_skill is not None: self.state["current_skill"] = current_skill
        
        try:
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            with open(self.persistence_file, 'w') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"Session: Erro ao salvar estado: {e}")

    def load(self):
        """Carrega o último estado salvo."""
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, 'r') as f:
                    self.state = json.load(f)
                return self.state
            except Exception as e:
                print(f"Session: Erro ao carregar estado: {e}")
        return self.state

# Instância global
session_persistence = SessionPersistence()
