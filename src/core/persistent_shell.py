import subprocess
import threading
import os
import time
import uuid

class PersistentShell:
    """
    Mantém uma sessão de shell viva para preservar o estado (cd, env vars).
    Fallback robusto: se o shell morrer ou timeout, usa subprocess.run direto.
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
        
        self.process = None
        self.sentinel = f"__OMNI_DONE_{uuid.uuid4().hex}__"
        self._start_shell()
        self._initialized = True

    def _start_shell(self):
        """Inicia ou reinicia a sessão zsh."""
        try:
            self.process = subprocess.Popen(
                ["zsh", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=os.environ.copy()
            )
            print("PersistentShell: Sessão ZSH iniciada.")
        except Exception as e:
            print(f"PersistentShell: Falha ao iniciar ZSH: {e}")
            self.process = None

    def execute(self, command, timeout=30):
        """Executa um comando e retorna o output. Fallback para subprocess.run direto."""
        # Tenta usar shell persistente primeiro
        if self.process and self.process.poll() is None:
            try:
                return self._execute_persistent(command, timeout)
            except Exception as e:
                print(f"PersistentShell: Erro no shell persistente, usando fallback: {e}")
        
        # Fallback: subprocess.run direto (mais confiável)
        return self._execute_fallback(command, timeout)

    def _execute_persistent(self, command, timeout):
        """Executa via shell persistente com sentinel."""
        full_command = f"{command}; echo '{self.sentinel}'; echo '{self.sentinel}' >&2\n"
        
        self.process.stdin.write(full_command)
        self.process.stdin.flush()
        
        stdout_lines = []
        stderr_lines = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            line = self.process.stdout.readline()
            if self.sentinel in line:
                break
            stdout_lines.append(line)
        
        return {
            "stdout": "".join(stdout_lines).strip(),
            "stderr": "",
            "returncode": 0
        }

    def _execute_fallback(self, command, timeout):
        """Executa via subprocess.run direto (fallback seguro)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Timeout: comando excedeu {timeout}s.", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def __del__(self):
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
            except:
                pass

# Instância global
shell = PersistentShell()
