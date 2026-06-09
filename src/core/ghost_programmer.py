import time
import threading
from core.execution_service import ExecutionService
from core.context_service import ContextService
from PyQt6.QtCore import pyqtSignal, QObject

class GhostPairProgrammer(QObject):
    """
    Analisa silenciosamente o código que o usuário está escrevendo e sugere correções.
    """
    fix_suggested = pyqtSignal(str, str, str, str) # file, desc, old, new

    def __init__(self, llm_manager, voice_service, hud):
        super().__init__()
        self.llm = llm_manager
        self.voice = voice_service
        self.hud = hud
        self.running = False
        self.last_analysis_time = 0
        self.analysis_interval = 600 # 10 minutos
        self.last_file_path = ""

    def start(self):
        if self.running: return
        self.running = True
        import threading
        threading.Thread(target=self._run_loop, daemon=True).start()
        print("Overwatch: Pair Programmer Fantasma ativado.")

    def _run_loop(self):
        import time
        while self.running:
            current_time = time.time()
            if current_time - self.last_analysis_time > self.analysis_interval:
                self._perform_analysis()
                self.last_analysis_time = current_time
            time.sleep(30)

    def _perform_analysis(self):
        file_path = ExecutionService.get_vscode_current_file()
        if file_path == "unknown" or not file_path:
            return

        print(f"Overwatch: Analisando {file_path} em busca de melhorias...")
        content = ExecutionService.read_file(file_path)
        if len(content) < 50: return

        prompt = f"""Você é o JARVIS (Ghost Pair Programmer).
ARQUIVO: {file_path}
CONTEÚDO:
{content[:2000]}

SUA TAREFA:
Se encontrar um erro ou uma melhoria clara de Clean Code, responda com um JSON.
Se não encontrar nada relevante, responda "SILENCIO".

JSON FORMAT:
{{
  "description": "Explicação curta da melhoria",
  "old_text": "O trecho de código exato a ser substituído",
  "new_text": "O novo trecho de código melhorado"
}}
"""
        response = self.llm.generate_command(prompt, system_context="GHOST_FIX")
        
        clean_response = response.strip()
        if clean_response.upper() != "SILENCIO":
            try:
                import json
                # Tenta extrair JSON da resposta do LLM
                start = clean_response.find('{')
                end = clean_response.rfind('}') + 1
                if start != -1 and end != 0:
                    data = json.loads(clean_response[start:end])
                    self.fix_suggested.emit(
                        file_path,
                        data["description"],
                        data["old_text"],
                        data["new_text"]
                    )
            except Exception as e:
                print(f"Erro ao processar sugestão Ghost Fix: {e}")
