import psutil
from core.execution_service import ExecutionService

class SystemMonitor:
    @staticmethod
    def get_system_status():
        """Obtém status do sistema (apps rodando)."""
        return ExecutionService.send_command_to_swift({"action": "get_status"})

    @staticmethod
    def list_running_apps():
        """Retorna lista de apps rodando."""
        status = SystemMonitor.get_system_status()
        return status.get("running_apps", [])

    @staticmethod
    def get_active_app():
        """Retorna o bundle ID do app em foco."""
        return ExecutionService.send_command_to_swift({"action": "get_active_app"})

    @staticmethod
    def get_resource_usage():
        """Obtém uso de CPU, Memória, Bateria e processos intensivos."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()
            
            # Identifica processos "sequestradores" de CPU
            intensive_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > 50: # Mais de 50% de um núcleo
                        intensive_processes.append(proc.info)
                except: continue

            battery_info = {
                "percent": battery.percent if battery else 100,
                "power_plugged": battery.power_plugged if battery else True
            }
            
            return {
                "cpu": cpu,
                "memory": memory,
                "battery": battery_info,
                "top_processes": sorted(intensive_processes, key=lambda x: x['cpu_percent'], reverse=True)[:3]
            }
        except Exception as e:
            print(f"Erro ao obter recursos: {e}")
            return {"cpu": 0, "memory": 0, "battery": {"percent": 100, "power_plugged": True}, "top_processes": []}
