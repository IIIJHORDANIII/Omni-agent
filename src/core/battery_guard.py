import psutil
import threading
import time
from datetime import datetime

class BatteryGuard:
    """
    Modo economico de bateria - adapta automaticamente o comportamento
    do agente quando o Mac esta na bateria.
    """
    
    def __init__(self, voice_service=None, hud=None):
        self.voice = voice_service
        self.hud = hud
        self._monitoring = False
        self._original_settings = {}
        self._is_battery_mode = False
        
        # Thresholds
        self.LOW_BATTERY_THRESHOLD = 20
        self.CRITICAL_BATTERY_THRESHOLD = 10
        
        # Callbacks
        self.on_battery_change = None

    def start_monitoring(self, interval=30):
        """Inicia monitoramento de bateria em background."""
        if self._monitoring:
            return
        self._monitoring = True
        
        def _monitor():
            while self._monitoring:
                self._check_battery()
                time.sleep(interval)
        
        thread = threading.Thread(target=_monitor, daemon=True)
        thread.start()

    def stop_monitoring(self):
        """Para o monitoramento."""
        self._monitoring = False

    def _check_battery(self):
        """Verifica estado da bateria e aplica modo economico."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return
            
            percent = battery.percent
            plugged = battery.power_plugged
            
            # Ativa modo economico se na bateria e abaixo do threshold
            if not plugged and percent <= self.LOW_BATTERY_THRESHOLD:
                if not self._is_battery_mode:
                    self._activate_battery_mode(percent)
            elif self._is_battery_mode and (plugged or percent > self.LOW_BATTERY_THRESHOLD + 5):
                self._deactivate_battery_mode()
            
            # Alertas criticos
            if percent <= self.CRITICAL_BATTERY_THRESHOLD and not plugged:
                self._notify(
                    "Bateria Critica!",
                    f"Apenas {percent}% restante. Conecte o carregador."
                )
        except Exception:
            pass

    def _activate_battery_mode(self, percent):
        """Ativa modo economico de bateria."""
        self._is_battery_mode = True
        
        try:
            from core.hardware_manager import HardwareManager
            
            # Reduz brilho
            HardwareManager.set_brightness(40)
            
            # Reduz volume
            HardwareManager.set_volume(30)
            
            self._notify(
                f"Modo Economico Ativado ({percent}%)",
                "Brilho e volume reduzidos para economizar bateria"
            )
            
            if self.on_battery_change:
                self.on_battery_change(True, percent)
        except Exception:
            pass

    def _deactivate_battery_mode(self):
        """Desativa modo economico."""
        self._is_battery_mode = False
        
        try:
            from core.hardware_manager import HardwareManager
            
            # Restaura brilho e volume
            HardwareManager.set_brightness(80)
            HardwareManager.set_volume(50)
            
            self._notify("Modo Economico Desativado", "Configuracoes restauradas")
            
            if self.on_battery_change:
                self.on_battery_change(False, 100)
        except Exception:
            pass

    def get_status(self):
        """Retorna status atual da bateria."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {"available": False, "message": "Bateria nao detectada"}
            
            remaining = None
            if battery.secsleft and battery.secsleft > 0:
                remaining = self._format_time(battery.secsleft)
            
            return {
                "available": True,
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "remaining": remaining,
                "battery_mode": self._is_battery_mode,
                "time_left_raw": battery.secsleft
            }
        except Exception:
            return {"available": False, "message": "Erro ao ler bateria"}

    def _format_time(self, seconds):
        """Formata segundos em HH:MM."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}min"
        return f"{minutes}min"

    def _notify(self, title, message):
        """Notifica via HUD e voz."""
        if self.hud:
            try:
                self.hud.display_signal.emit(title, "PROACTIVE", 4000)
            except Exception:
                pass
        if self.voice:
            try:
                self.voice.speak(f"{title}. {message}")
            except Exception:
                pass
