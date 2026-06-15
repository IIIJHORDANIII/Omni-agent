import os
import subprocess
import time
import threading
from datetime import datetime
from core.execution_service import ExecutionService

class NightWatch:
    """
    Protocolo Night Watch: Autocura autonoma durante a inatividade.
    Monitora inatividade do usuario e executa patrulhas automaticamente.
    """
    # Intervalos de verificacao (em segundos)
    CHECK_INTERVAL = 300       # Verifica inatividade a cada 5 min
    INACTIVITY_THRESHOLD = 1800  # 30 min sem atividade = considera inativo
    PATROL_COOLDOWN = 3600     # Intervalo minimo entre patrulhas automaticas

    def __init__(self, llm_manager):
        self.llm = llm_manager
        self._monitoring = False
        self._monitor_thread = None
        self._last_patrol_time = 0
        self._last_activity_time = time.time()
        self._idle_start = None

    def start(self):
        """Inicia o monitoramento de inatividade em background."""
        if self._monitoring:
            return "Night Watch ja esta em monitoramento."
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print("Night Watch: Monitoramento de inatividade iniciado.")
        return "Night Watch: Monitoramento ativo."

    def stop(self):
        """Para o monitoramento de inatividade."""
        self._monitoring = False
        print("Night Watch: Monitoramento parado.")
        return "Night Watch: Monitoramento encerrado."

    def _monitor_loop(self):
        """Loop principal de monitoramento de inatividade."""
        while self._monitoring:
            time.sleep(self.CHECK_INTERVAL)
            if not self._monitoring:
                break
            try:
                idle_seconds = self._get_idle_time()
                if idle_seconds >= self.INACTIVITY_THRESHOLD:
                    now = time.time()
                    if now - self._last_patrol_time >= self.PATROL_COOLDOWN:
                        print(f"Night Watch: Inatividade detectada ({idle_seconds}s). Iniciando patrulha automatica...")
                        self.run_nightly_patrol()
                        self._last_patrol_time = now
            except Exception as e:
                print(f"Night Watch: Erro no monitoramento: {e}")

    def _get_idle_time(self):
        """Retorna o tempo de inatividade do usuario em segundos usando ioreg."""
        try:
            # Usa ioreg para obter tempo de inatividade do HID (Human Interface Device)
            result = subprocess.run(
                ['ioreg', '-c', 'IOHIDSystem'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'HIDIdleTime' in line:
                    # Formato: "HIDIdleTime" = 123456789 (em nanosegundos)
                    parts = line.split('=')
                    if len(parts) == 2:
                        ns = int(parts[1].strip())
                        return ns / 1_000_000_000  # Converte para segundos
        except Exception:
            pass
        # Fallback: retorna 0 (assume ativo)
        return 0

    def run_nightly_patrol(self):
        """Executa a patrulha noturna: testes e correcoes."""
        print("Night Watch: Iniciando patrulha noturna...")
        report = []

        # 1. Identifica o projeto atual
        project_root = os.getcwd()
        report.append(f"Projeto: {project_root}")
        report.append(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # 2. Roda testes
        test_result = self._run_tests(project_root)
        if "FAILED" in test_result or "ERRORS" in test_result:
            report.append("Status: FALHAS DETECTADAS")
            print("Night Watch: Falhas detectadas! Iniciando tentativa de autocura...")
            heal_result = self._attempt_healing(project_root, test_result)
            report.append(f"Autocura: {heal_result}")
        else:
            report.append("Status: TESTES OK")
            print("Night Watch: Todos os testes passaram. Sistema saudavel.")

        # 3. Verifica branches nao mergeadas
        branch_info = self._check_unmerged_branches(project_root)
        if branch_info:
            report.append(f"Branches pendentes: {branch_info}")

        # 4. Verifica espaco em disco
        disk_check = self._check_disk_space()
        report.append(f"Disco: {disk_check}")

        return "\n".join(report)

    def _check_unmerged_branches(self, project_root):
        """Lista branches que nao foram mergeadas no main."""
        try:
            result = subprocess.run(
                ['git', '-C', project_root, 'branch', '--no-merged', 'main'],
                capture_output=True, text=True, timeout=10
            )
            branches = [b.strip().replace('* ', '') for b in result.stdout.strip().split('\n') if b.strip()]
            if branches:
                return ", ".join(branches[:5])
        except Exception:
            pass
        return None

    def _check_disk_space(self):
        """Verifica espaco livre em disco (alerta se < 10GB)."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024**3)
            if free_gb < 10:
                return f"ALERTA: {free_gb:.1f}GB livres"
            return f"{free_gb:.1f}GB livres"
        except Exception:
            return "Nao foi possivel verificar"

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
