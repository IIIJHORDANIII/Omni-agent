import subprocess
import tempfile
import os
import uuid

class SandboxService:
    """
    Executa código Python de forma isolada usando Docker.
    Garante que a IA não afete o host.
    """
    
    @staticmethod
    def execute_python(code):
        """Roda o código em um container e retorna o output."""
        # Cria um arquivo temporário para o código
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp.write(code.encode('utf-8'))
            tmp_path = tmp.name
        
        try:
            # Comando Docker:
            # - --rm: Remove container ao fim
            # - -v: Monta o script dentro do container
            # - python:3.11-slim: Imagem leve
            container_path = f"/tmp/{os.path.basename(tmp_path)}"
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{tmp_path}:{container_path}",
                "python:3.11-slim",
                "python", container_path
            ]
            
            print(f"Sandbox: Iniciando container para execução segura...")
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

# Instância global
sandbox = SandboxService()
