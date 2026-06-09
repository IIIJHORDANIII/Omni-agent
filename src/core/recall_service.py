import time
import threading
from core.vision_service import VisionService
from core.memory_client import MemoryClient

class RecallService:
    """
    Protocolo Recall: Captura e indexa visualmente o que o usuário está fazendo.
    """
    def __init__(self, llm_manager):
        self.vision = None # Injetado pelo main.py
        self.memory = MemoryClient()
        self.llm = llm_manager
        self.running = False
        self.interval = 300 # 5 minutos

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._recall_loop, daemon=True).start()
        print("Protocolo Recall: Memória fotográfica ativada.")

    def _recall_loop(self):
        # Aguarda o sistema estabilizar após o boot (30s)
        time.sleep(30)
        while self.running:
            try:
                if self.vision:
                    self._take_snapshot()
            except Exception as e:
                print(f"Erro no snapshot do Recall: {e}")
            time.sleep(self.interval)

    def _take_snapshot(self):
        """Captura a tela, gera tags semânticas e salva na memória."""
        print("Recall: Capturando momento visual...")
        description = self.vision.describe_screen("Descreva em 10 palavras-chave o que está acontecendo nesta tela (apps, tópicos, sites).")
        
        if "Erro" in description: return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        observation = f"Recall [{timestamp}]: O usuário estava focado em: {description}"
        
        # Salva na memória episódica
        self.memory.store_observation(observation)
        print(f"Recall: Momento indexado: {description}")

    def stop(self):
        self.running = False
