import os
import threading
import time
import subprocess
from core.execution_service import ExecutionService

class LogWatcherService:
    """
    Monitora arquivos de log ou saídas de terminal em busca de erros proativamente.
    """
    def __init__(self, llm_manager, voice_service, hud):
        self.llm = llm_manager
        self.voice = voice_service
        self.hud = hud
        self.running = False
        self.monitored_files = []
        self.last_positions = {}

    def add_log_file(self, path):
        full_path = os.path.expanduser(path)
        if os.path.exists(full_path):
            self.monitored_files.append(full_path)
            self.last_positions[full_path] = os.path.getsize(full_path)
            print(f"Overwatch: Monitorando log em {full_path}")

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
        while self.running:
            for log_path in self.monitored_files:
                self._check_file(log_path)
            time.sleep(2) # Verifica a cada 2 segundos

    def _check_file(self, path):
        try:
            current_size = os.path.getsize(path)
            if current_size < self.last_positions[path]:
                # Arquivo foi rotacionado ou limpo
                self.last_positions[path] = 0
            
            if current_size > self.last_positions[path]:
                with open(path, 'r') as f:
                    f.seek(self.last_positions[path])
                    new_data = f.read()
                    self.last_positions[path] = current_size
                    
                    if "Error" in new_data or "Exception" in new_data or "failed" in new_data.lower():
                        self._analyze_error(new_data, path)
        except Exception as e:
            print(f"Erro ao ler log {path}: {e}")

    def _analyze_error(self, error_text, source):
        print(f"Overwatch detectou uma anomalia em {os.path.basename(source)}!")
        
        prompt = f"""Você é o JARVIS (Protocolo Overwatch).
Detectamos o seguinte erro em um arquivo de log:

LOG:
{error_text[-1000:]}

SUA TAREFA:
1. Explique o erro de forma curtíssima.
2. Sugira uma solução imediata.

REGRAS:
- Seja proativo.
- Se for um erro comum (CORS, Port in use, Syntax), seja direto.
- Responda em português.
"""
        response = self.llm.generate_command(prompt, system_context="OVERWATCH_LOG_MONITOR")
        
        # Alerta o usuário
        self.hud.display_signal.emit(f"ANOMALIA DETECTADA: {os.path.basename(source)}", "THINKING", 5000)
        self.voice.speak(f"Senhor, detectei um erro no log do {os.path.basename(source)}. {response}")
