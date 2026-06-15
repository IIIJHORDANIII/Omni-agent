import os
import time
import subprocess
import threading
from watchdog.events import FileSystemEventHandler

class CodeQualityHandler(FileSystemEventHandler):
    """Monitora alterações de código e dispara linters proativamente."""
    def __init__(self, main_app, target_path):
        self.main_app = main_app
        self.target_path = target_path
        self.last_check = 0
        self.cooldown = 3 # Segundos entre verificações por arquivo

    def on_modified(self, event):
        if event.is_directory: return
        if time.time() - self.last_check < self.cooldown: return
        
        filename = event.src_path
        if filename.endswith(('.py', '.ts', '.js', '.tsx', '.jsx')):
            self.last_check = time.time()
            threading.Thread(target=self.run_lint, args=(filename,), daemon=True).start()

    def run_lint(self, file_path):
        """Executa o linter adequado baseado na extensão."""
        ext = os.path.splitext(file_path)[1]
        rel_path = os.path.relpath(file_path, self.target_path)
        
        print(f"Background Agent: Revisando {rel_path}...")
        
        cmd = []
        if ext == '.py':
            # Usa Ruff (muito rápido) se disponível, senão flake8
            cmd = ["ruff", "check", file_path]
        elif ext in ['.ts', '.js', '.tsx', '.jsx']:
            cmd = ["npx", "eslint", file_path, "--quiet"]
            
        if not cmd: return

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # Encontrou problemas! Avisa no HUD de forma discreta
                msg = f"Problema detectado em {os.path.basename(file_path)}"
                self.main_app.hud.display_signal.emit(msg, "THINKING", 4000)
                # Opcional: registrar na memória para o briefing
                self.main_app.chat_window.llm_client.memory_client.store_observation(
                    f"Erro de linting em {rel_path}: {result.stdout[:100]}"
                )
        except Exception as e:
            print(f"Erro ao rodar linter em background: {e}")

class BackgroundAgentService:
    """Orquestrador de agentes que rodam sem intervenção do usuário."""
    def __init__(self, main_app):
        self.main_app = main_app
        self.target_project = os.path.expanduser("~/Documents/pessoal/payjota/app-payjota")
        self.running = False

    def start(self, observer):
        if not os.path.exists(self.target_project):
            print(f"Aviso: Projeto {self.target_project} não encontrado para monitoramento de background.")
            return

        # 1. Inicia o Linting Watcher
        quality_handler = CodeQualityHandler(self.main_app, self.target_project)
        observer.schedule(quality_handler, self.target_project, recursive=True)
        
        # 2. Inicia o Dependency Scout (roda a cada 24h ou no startup)
        threading.Thread(target=self._run_dependency_scout, daemon=True).start()
        
        self.running = True
        print(f"Agentes de Background ATIVADOS para: {self.target_project}")

    def _run_dependency_scout(self):
        """Verifica saúde das dependências do projeto."""
        # Aguarda um pouco o startup
        time.sleep(10)
        print("Dependency Scout: Iniciando varredura semanal...")
        
        # Exemplo: Procura package.json e roda audit
        pkg_json = os.path.join(self.target_project, "package.json")
        if os.path.exists(pkg_json):
            try:
                res = subprocess.run(["npm", "audit", "--json"], cwd=self.target_project, capture_output=True, text=True)
                # Se houver vulnerabilidades críticas, cria uma nota
                if "critical" in res.stdout.lower():
                    self.main_app.hud.display_signal.emit("Vulnerabilidade Crítica detectada!", "PROACTIVE", 6000)
                    self.main_app.chat_window.llm_client.execution_service.create_new_note(
                        "Segurança: app-payjota",
                        f"O Dependency Scout detectou vulnerabilidades no projeto.\n\nResultado do audit:\n{res.stdout[:2000]}"
                    )
            except: pass
