import psutil
import time
import threading
from core.execution_service import ExecutionService

class ResourceGuard:
    # Threshold de CPU em porcentagem para considerar "pesado"
    CPU_THRESHOLD = 80.0
    _monitoring = False

    @staticmethod
    def check_and_kill_heavy_processes():
        """Monitora processos e encerra se consumirem muita CPU."""
        killed = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] and proc.info['cpu_percent'] > ResourceGuard.CPU_THRESHOLD:
                    # Nunca mata processos críticos do sistema
                    name = (proc.info['name'] or '').lower()
                    if name in ('kernel_task', 'WindowServer', 'mds', 'mds_stores', 'launchd', 'sudo', 'python'):
                        continue
                    
                    print(f"ResourceGuard: Processo {proc.info['name']} (PID: {proc.info['pid']}) consumindo {proc.info['cpu_percent']}%")
                    
                    ExecutionService.send_command_to_swift({
                        "action": "terminate_pid", 
                        "pid": str(proc.info['pid'])
                    })
                    killed.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return killed
    
    @staticmethod
    def start_monitoring(interval=10.0):
        """Inicia monitoramento em background thread."""
        if ResourceGuard._monitoring:
            return
        ResourceGuard._monitoring = True
        
        def _monitor_loop():
            print("ResourceGuard: Monitoramento de CPU ativo.")
            while ResourceGuard._monitoring:
                ResourceGuard.check_and_kill_heavy_processes()
                time.sleep(interval)
        
        thread = threading.Thread(target=_monitor_loop, daemon=True)
        thread.start()
