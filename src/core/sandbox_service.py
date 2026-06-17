import subprocess
import tempfile
import os
import uuid

class SandboxService:
    """
    Executa código Python de forma isolada usando Docker.
    Se Docker não estiver disponível, faz fallback local (exec direto).
    """
    
    _docker_available = None
    
    @classmethod
    def _check_docker(cls):
        if cls._docker_available is None:
            try:
                result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
                cls._docker_available = result.returncode == 0
            except Exception:
                cls._docker_available = False
        return cls._docker_available
    
    @staticmethod
    def execute_python(code):
        """Roda o código em container (se Docker disponível) ou localmente."""
        if SandboxService._check_docker():
            return SandboxService._execute_in_docker(code)
        else:
            return SandboxService._execute_local(code)
    
    @staticmethod
    def _execute_in_docker(code):
        """Executa código em container Docker isolado."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp.write(code.encode('utf-8'))
            tmp_path = tmp.name
        
        try:
            container_path = f"/tmp/{os.path.basename(tmp_path)}"
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{tmp_path}:{container_path}",
                "python:3.11-slim",
                "python", container_path
            ]
            
            print(f"Sandbox: Iniciando container Docker para execução segura...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return f"Sandbox Output:\n{result.stdout.strip()}"
            else:
                return f"Sandbox Erro:\n{result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            return "Erro: Sandbox atingiu o tempo limite (30s)."
        except Exception as e:
            return f"Erro na Sandbox: {str(e)}"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    @staticmethod
    def _execute_local(code):
        """Executa codigo Python localmente (fallback sem Docker)."""
        import sys
        import io

        # Bloqueio de padroes perigosos
        dangerous = ['import os', 'import subprocess', 'os.system', 'subprocess.run',
                     '__import__', 'exec(', 'eval(', 'open(']
        code_lower = code.lower()
        for d in dangerous:
            if d in code_lower:
                return f"Erro de seguranca: operacao '{d}' nao permitida no sandbox local."

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = sys.stdout = io.StringIO()
        redirected_error = sys.stderr = io.StringIO()
        
        try:
            # Builtins restritos
            safe_builtins = {
                k: v for k, v in __builtins__.items()
                if k not in ('__import__', 'exec', 'eval', 'compile', 'open', 'breakpoint')
            } if isinstance(__builtins__, dict) else __builtins__
            exec(code, {"__builtins__": safe_builtins})
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            output = redirected_output.getvalue()
            errors = redirected_error.getvalue()
            
            if errors:
                return f"Output:\n{output}\nAvisos/Erros:\n{errors}"
            return output or "Codigo executado com sucesso (sem output)."
        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            return f"Erro na execucao: {e}"

# Instância global
sandbox = SandboxService()
