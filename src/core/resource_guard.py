import psutil
import time
from core.execution_service import ExecutionService

class ResourceGuard:
    # Threshold de CPU em porcentagem para considerar "pesado"
    CPU_THRESHOLD = 80.0
    
    @staticmethod
    def check_and_kill_heavy_processes():
        """Monitora processos e encerra se consumirem muita CPU."""
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                # cpu_percent precisa de um intervalo para calcular, 
                # aqui usamos o último cálculo registrado
                if proc.info['cpu_percent'] and proc.info['cpu_percent'] > ResourceGuard.CPU_THRESHOLD:
                    print(f"DEBUG: Processo {proc.info['name']} (PID: {proc.info['pid']}) consumindo {proc.info['cpu_percent']}%")
                    
                    # Envia comando para Swift matar o PID
                    ExecutionService.send_command_to_swift({
                        "action": "terminate_pid", 
                        "pid": str(proc.info['pid'])
                    })
                    print(f"DEBUG: Processo {proc.info['pid']} encerrado.")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    @staticmethod
    def start_monitoring(interval=5.0):
        print("Resource Guard ativo...")
        while True:
            ResourceGuard.check_and_kill_heavy_processes()
            time.sleep(interval)
