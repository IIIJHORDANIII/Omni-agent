import subprocess
import threading
import os
import time
import uuid

class PersistentShell:
    """
    Mantém uma sessão de shell viva para preservar o estado (cd, env vars).
    Usa um sentinel único para detectar o fim da execução de cada comando.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PersistentShell, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        
        # Inicia o processo zsh (nativo macOS)
        self.process = subprocess.Popen(
            ["zsh", "-i"], # Modo interativo para carregar aliases se houver
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1, # Line buffered
            env=os.environ.copy()
        )
        
        self.sentinel = f"__ANDERS_DONE_{uuid.uuid4().hex}__"
        self._initialized = True
        print("PersistentShell: Sessão ZSH iniciada.")

    def execute(self, command, timeout=15):
        """Executa um comando e retorna o output até o sentinel."""
        if not self.process or self.process.poll() is not None:
            self._initialized = False
            self.__init__() # Reinicia se morreu

        # Limpa o comando e adiciona o eco do sentinel
        full_command = f"{command}; echo '{self.sentinel}'; echo '{self.sentinel}' >&2\n"
        
        try:
            self.process.stdin.write(full_command)
            self.process.stdin.flush()
            
            stdout_lines = []
            stderr_lines = []
            
            start_time = time.time()
            
            # Leitura não-bloqueante (simplificada para este ambiente)
            while time.time() - start_time < timeout:
                # Nota: Esta implementação de leitura é síncrona para simplificar o loop.
                # Em produção real, usaríamos threads ou select para ler stdout/stderr em paralelo.
                line = self.process.stdout.readline()
                if self.sentinel in line:
                    break
                stdout_lines.append(line)
            
            # Tenta pegar erros se houver
            # (Em zsh interativo, o stderr pode ser barulhento, então filtramos)
            
            return {
                "stdout": "".join(stdout_lines).strip(),
                "stderr": "", # Simplificado: zsh interativo mistura muito stderr
                "returncode": 0 # Presumimos 0 se o sentinel chegou
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def __del__(self):
        if hasattr(self, 'process') and self.process:
            self.process.terminate()

# Instância global
shell = PersistentShell()
