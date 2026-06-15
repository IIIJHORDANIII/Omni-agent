import time
import threading
from core.vision_service import VisionService
from core.system_monitor import SystemMonitor

class SentinelService:
    """
    Protocolo Sentinela: Monitoramento visual adaptativo.
    Se estiver no carregador: Monitoramento contínuo (Estilo JARVIS).
    Se estiver na bateria: Monitoramento econômico.
    """
    def __init__(self, voice_service, hud):
        self.vision = VisionService()
        self.voice = voice_service
        self.hud = hud
        self.running = False
        self.is_user_present = True
        self.check_interval_ac = 10 # 10 segundos no AC
        self.check_interval_bat = 300 # 5 minutos na bateria
        
    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._sentinel_loop, daemon=True).start()
        print("Protocolo Sentinela: Monitoramento visual adaptativo ativado.")

    def _sentinel_loop(self):
        while self.running:
            try:
                status = SystemMonitor.get_resource_usage()
                is_plugged = status["battery"]["power_plugged"]
                
                # Executa o reconhecimento
                was_present = self.is_user_present
                self.is_user_present = self.vision.recognize_user()
                
                # Reações
                if was_present and not self.is_user_present:
                    print("Sentinela: Jhordan se ausentou.")
                    self.hud.display_signal.emit("SENTINELA: Usuário ausente", "IDLE", 3000)
                elif not was_present and self.is_user_present:
                    print("Sentinela: Jhordan retornou.")
                    self.voice.speak("Bem-vindo de volta, Jhordan. Estou à disposição.")
                    self.hud.display_signal.emit("SENTINELA: Identidade confirmada", "SUCCESS", 3000)

                # Define o próximo intervalo baseado na energia
                if is_plugged:
                    time.sleep(self.check_interval_ac)
                else:
                    time.sleep(self.check_interval_bat)
                    
            except Exception as e:
                print(f"Erro no loop do Sentinela: {e}")
                time.sleep(60)

    def stop(self):
        self.running = False
