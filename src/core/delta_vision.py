import threading
import time
import numpy as np
from PIL import Image, ImageChops
from core.vision_service import VisionService

class DeltaVisionService:
    """
    Detecta mudanças drásticas na tela para alertar o usuário proativamente.
    """
    def __init__(self, voice_service, hud):
        self.vision = VisionService()
        self.voice = voice_service
        self.hud = hud
        self.last_img = None
        self.running = False
        self.cooldown = 30 # Segundos entre alertas proativos

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        print("Delta-Vision: Monitoramento proativo ativado.")

    def _monitor_loop(self):
        while self.running:
            try:
                # 1. Captura rápida (baixa res para economizar Metal)
                img = self.vision.capture_screen_pil()
                if img is None: 
                    time.sleep(5)
                    continue
                
                img_small = img.resize((256, 256)).convert("L")
                
                if self.last_img:
                    # 2. Calcula diferença (Delta)
                    diff = ImageChops.difference(img_small, self.last_img)
                    stat = np.array(diff).mean()
                    
                    # Se a mudança for > 15% (limiar empírico para janelas novas/erros)
                    if stat > 40: # Valor de brilho médio da diferença
                        print(f"Delta-Vision: Mudança detectada ({stat:.2f}). Analisando...")
                        self._analyze_change()
                        time.sleep(self.cooldown)
                
                self.last_img = img_small
                time.sleep(10) # Checa a cada 10s
                
            except Exception as e:
                print(f"Delta-Vision Erro: {e}")
                time.sleep(10)

    def _analyze_change(self):
        """Usa o Qwen2-VL para entender o que mudou e se é relevante."""
        prompt = "Houve uma mudança importante na tela agora. Detecte se há mensagens de erro, alertas de sistema ou mudanças críticas. Se for algo irrelevante (como abrir um site comum), responda apenas 'SKIP'. Se for importante, descreva o que aconteceu."
        
        description = self.vision.describe_screen(prompt)
        
        if description and "SKIP" not in description.upper():
            self.hud.display_signal.emit(f"ALERTA VISUAL: {description[:50]}...", "PROACTIVE", 5000)
            self.voice.speak(f"Senhor, notei uma mudança na sua tela. {description}")

# Instância global gerenciada pelo MainApp
