import os
import subprocess
import time
from core.execution_service import ExecutionService

class NightWatch:
    """
    Protocolo Night Watch: Autocura autônoma durante a inatividade.
    """
    def __init__(self, llm_manager):
        self.llm = llm_manager

    def run_nightly_patrol(self):
        """Executa a patrulha noturna: testes e correções."""
        print("Night Watch: Iniciando patrulha noturna...")
        
        # 1. Identifica o projeto atual
        project_root = os.getcwd()
        
        # 2. Roda testes (exemplo com pytest)
        test_result = self._run_tests(project_root)
        
        if "FAILED" in test_result or "ERRORS" in test_result:
            print("Night Watch: Falhas detectadas! Iniciando tentativa de autocura...")
            self._attempt_healing(project_root, test_result)
        else:
            print("Night Watch: Todos os testes passaram. Sistema saudável.")

    def _run_tests(self, path):
        """Executa testes e captura saída."""
        try:
            # Tenta pytest primeiro
            res = subprocess.run(["pytest", path], capture_output=True, text=True, timeout=120)
            return res.stdout + res.stderr
        except:
            return "Erro ao rodar testes."

    def _attempt_healing(self, path, test_output):
        """Tenta corrigir o código com base na falha do teste."""
        prompt = f"""Você é o JARVIS (Protocolo Night Watch).
Os testes do projeto falharam conforme o log abaixo:

LOG DE ERRO:
{test_output[:2000]}

SUA TAREFA:
1. Analise o log e identifique o arquivo e a linha do erro.
2. Gere a correção necessária.
3. Responda com um JSON indicando o arquivo e a mudança.

JSON FORMAT:
{{
  "file": "caminho/do/arquivo.py",
  "old_code": "trecho original",
  "new_code": "trecho corrigido",
  "explanation": "por que falhou?"
}}
"""
        response = self.llm.generate_command(prompt, system_context="NIGHT_WATCH_HEALING")
        
        try:
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            data = json.loads(response[start:end])
            
            # Aplica a correção em uma nova branch
            branch_name = f"jarvis/night-watch-fix-{int(time.time())}"
            subprocess.run(["git", "checkout", "-b", branch_name])
            
            content = ExecutionService.read_file(data["file"])
            if data["old_code"] in content:
                new_content = content.replace(data["old_code"], data["new_code"])
                ExecutionService.create_file(data["file"], new_content)
                
                subprocess.run(["git", "add", "."])
                subprocess.run(["git", "commit", "-m", f"Night Watch: {data['explanation']}"])
                print(f"Night Watch: Correção aplicada no branch {branch_name}")
            
        except Exception as e:
            print(f"Night Watch: Falha na tentativa de autocura: {e}")
