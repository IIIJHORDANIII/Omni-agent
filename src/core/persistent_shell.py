import subprocess
import threading
import os
import time
import uuid

class PersistentShell:
    """
    Mantém uma sessão de shell viva para preservar o estado (cd, env vars).
    Usa thread em background para leitura segura, evitando deadlocks.
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
        
        # Inicia o processo zsh
        self.process = subprocess.Popen(
            ["zsh", "-i"], # Modo interativo
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1, # Line buffered
            env=os.environ.copy()
        )
        
        self.output_buffer = []
        self._stop_event = threading.Event()
        
        def _read_stdout():
            while not self._stop_event.is_set():
                if self.process.poll() is not None:
                    break
                try:
                    line = self.process.stdout.readline()
                    if line:
                        self.output_buffer.append(line)
                except Exception:
                    break

        self.reader_thread = threading.Thread(target=_read_stdout, daemon=True)
        self.reader_thread.start()

        self._initialized = True
        print("PersistentShell: Sessão ZSH iniciada (com thread de leitura segura).")

    def execute(self, command, timeout=15):
        """Executa um comando e retorna o output até o sentinel. Protegido contra travamentos."""
        if not self.process or self.process.poll() is not None:
            self._initialized = False
            self.__init__() # Reinicia se morreu

        # Limpa o buffer antes de executar novo comando
        self.output_buffer.clear()
        
        sentinel = f"__ANDERS_DONE_{uuid.uuid4().hex}__"
        full_command = f"{command}; echo '{sentinel}'\n"
        
        try:
            self.process.stdin.write(full_command)
            self.process.stdin.flush()
            
            start_time = time.time()
            result_lines = []
            
            while time.time() - start_time < timeout:
                if self.output_buffer:
                    line = self.output_buffer.pop(0)
                    if sentinel in line:
                        return {
                            "stdout": "".join(result_lines).strip(),
                            "stderr": "", 
                            "returncode": 0 
                        }
                    result_lines.append(line)
                else:
                    time.sleep(0.05)
            
            # Se chegou aqui, deu TIMEOUT. O comando travou (esperando input, etc).
            print(f"PersistentShell: TIMEOUT executando '{command}'. Reiniciando shell.")
            self.__del__()
            self._initialized = False
            return {
                "stdout": "".join(result_lines).strip() + "\n[Erro: Comando travou ou demorou muito. Processo cancelado.]",
                "stderr": "",
                "returncode": 1
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def __del__(self):
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
        if hasattr(self, 'process') and self.process:
            self.process.terminate()

# Instância global
shell = PersistentShell()
