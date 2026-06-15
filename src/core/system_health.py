import psutil
import os
import subprocess
from datetime import datetime

class SystemHealth:
    """
    Monitor de saude do sistema com verificacoes proativas
    e alertas inteligentes.
    """
    
    # Thresholds
    DISK_WARNING_GB = 10
    DISK_CRITICAL_GB = 5
    MEMORY_WARNING_PERCENT = 85
    MEMORY_CRITICAL_PERCENT = 95
    CPU_WARNING_PERCENT = 90
    UPTIME_WARNING_HOURS = 72
    
    def __init__(self, hud=None):
        self.hud = hud

    def check_all(self):
        """Executa todas as verificacoes e retorna relatorio."""
        checks = {
            "disk": self.check_disk(),
            "memory": self.check_memory(),
            "cpu": self.check_cpu(),
            "battery": self.check_battery(),
            "uptime": self.check_uptime(),
            "network": self.check_network(),
            "storage_health": self.check_storage_health(),
        }
        
        # Gera resumo geral
        issues = []
        for name, result in checks.items():
            if result.get("status") == "warning":
                issues.append(f"AVISO: {name} - {result.get('message', '')}")
            elif result.get("status") == "critical":
                issues.append(f"CRITICO: {name} - {result.get('message', '')}")
        
        checks["overall_status"] = "critical" if any(c.get("status") == "critical" for c in checks.values()) else "warning" if issues else "ok"
        checks["issues"] = issues
        
        return checks

    def check_disk(self):
        """Verifica espaco em disco."""
        try:
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            used_percent = disk.percent
            
            if free_gb < self.DISK_CRITICAL_GB:
                status = "critical"
                message = f"Apenas {free_gb:.1f}GB livres! Limpe arquivos."
            elif free_gb < self.DISK_WARNING_GB:
                status = "warning"
                message = f"{free_gb:.1f}GB livres. Considere limpar."
            else:
                status = "ok"
                message = f"{free_gb:.1f}GB livres ({used_percent}% usado)"
            
            return {
                "status": status,
                "message": message,
                "free_gb": round(free_gb, 1),
                "used_percent": used_percent,
                "total_gb": round(disk.total / (1024**3), 1)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_memory(self):
        """Verifica uso de memoria."""
        try:
            mem = psutil.virtual_memory()
            
            if mem.percent >= self.MEMORY_CRITICAL_PERCENT:
                status = "critical"
                message = f"Memoria critica: {mem.percent}%! Feche apps."
            elif mem.percent >= self.MEMORY_WARNING_PERCENT:
                status = "warning"
                message = f"Memoria alta: {mem.percent}%"
            else:
                status = "ok"
                message = f"Memoria: {mem.percent}% ({self._format_bytes(mem.available)} livres)"
            
            return {
                "status": status,
                "message": message,
                "percent": mem.percent,
                "available_gb": round(mem.available / (1024**3), 1),
                "total_gb": round(mem.total / (1024**3), 1)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_cpu(self):
        """Verifica uso de CPU."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            if cpu_percent >= self.CPU_WARNING_PERCENT:
                status = "warning"
                message = f"CPU alta: {cpu_percent}%"
            else:
                status = "ok"
                message = f"CPU: {cpu_percent}% ({cpu_count} nucleos)"
            
            return {
                "status": status,
                "message": message,
                "percent": cpu_percent,
                "cores": cpu_count,
                "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else None
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_battery(self):
        """Verifica estado da bateria."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {"status": "ok", "message": "Desktop (sem bateria)"}
            
            percent = battery.percent
            plugged = battery.power_plugged
            
            if not plugged and percent <= 10:
                status = "critical"
                message = f"Bateria critica: {percent}%!"
            elif not plugged and percent <= 20:
                status = "warning"
                message = f"Bateria baixa: {percent}% - Conecte o carregador"
            else:
                status = "ok"
                remaining = ""
                if battery.secsleft > 0:
                    hours = battery.secsleft // 3600
                    mins = (battery.secsleft % 3600) // 60
                    remaining = f" ({hours}h {mins}min restantes)"
                message = f"Bateria: {percent}%{'(carregando)' if plugged else remaining}"
            
            return {
                "status": status,
                "message": message,
                "percent": percent,
                "plugged": plugged
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_uptime(self):
        """Verifica tempo de atividade do sistema."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            uptime_hours = uptime_seconds / 3600
            
            if uptime_hours >= self.UPTIME_WARNING_HOURS:
                status = "warning"
                message = f"Sistema ligado ha {int(uptime_hours)}h. Considere reiniciar."
            else:
                status = "ok"
                days = int(uptime_hours // 24)
                hours = int(uptime_hours % 24)
                message = f"Uptime: {days}d {hours}h" if days > 0 else f"Uptime: {hours}h"
            
            return {
                "status": status,
                "message": message,
                "hours": round(uptime_hours, 1)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_network(self):
        """Verifica conectividade de rede."""
        try:
            # Testa conexao com um DNS publico
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                capture_output=True,
                timeout=5
            )
            connected = result.returncode == 0
            
            # Verifica interfaces de rede
            addrs = psutil.net_if_addrs()
            active_interfaces = []
            for iface, addr_list in addrs.items():
                for addr in addr_list:
                    if addr.family.name == 'AF_INET' and not addr.address.startswith('127.'):
                        active_interfaces.append(iface)
            
            return {
                "status": "ok" if connected else "warning",
                "message": "Rede conectada" if connected else "Sem conexao de rede",
                "connected": connected,
                "interfaces": active_interfaces
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_storage_health(self):
        """Verifica saude do armazenamento (SMART basico)."""
        try:
            # Verifica I/O stats
            disk_io = psutil.disk_io_counters()
            if disk_io:
                return {
                    "status": "ok",
                    "message": f"Leituras: {disk_io.read_count}, Escritas: {disk_io.write_count}",
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes
                }
            return {"status": "ok", "message": "Info de I/O indisponivel"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_top_processes(self, n=5):
        """Retorna os processos que mais consomem recursos."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Ordena por CPU
        by_cpu = sorted(processes, key=lambda p: p.get('cpu_percent', 0) or 0, reverse=True)[:n]
        
        # Ordena por Memoria
        by_mem = sorted(processes, key=lambda p: p.get('memory_percent', 0) or 0, reverse=True)[:n]
        
        return {
            "top_cpu": [{"name": p["name"], "pid": p["pid"], "cpu": p.get("cpu_percent", 0)} for p in by_cpu],
            "top_memory": [{"name": p["name"], "pid": p["pid"], "mem": round(p.get("memory_percent", 0), 1)} for p in by_mem]
        }

    def _format_bytes(self, bytes_val):
        """Formata bytes em formato legivel."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f}PB"

    def get_quick_status(self):
        """Retorna status rapido para o HUD."""
        disk = self.check_disk()
        mem = self.check_memory()
        cpu = self.check_cpu()
        
        return f"CPU {cpu['percent']}% | RAM {mem['percent']}% | Disco {disk['free_gb']}GB livre"
