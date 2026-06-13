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
        self.cooldown = 60 # Aumentado para 60s para ser menos intrusivo
        self.sensitivity = 60 # Aumentado de 40 para 60 (menos sensível a pequenas mudanças)

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        print("Delta-Vision: Monitoramento proativo ativado (Modo Silencioso).")

    def _monitor_loop(self):
        while self.running:
            try:
                # 1. Captura rápida
                img = self.vision.capture_screen_pil()
                if img is None: 
                    time.sleep(10)
                    continue
                
                img_small = img.resize((256, 256)).convert("L")
                
                if self.last_img:
                    # 2. Calcula diferença
                    diff = ImageChops.difference(img_small, self.last_img)
                    stat = np.array(diff).mean()
                    
                    if stat > self.sensitivity: 
                        print(f"Delta-Vision: Mudança detectada ({stat:.2f}).")
                        self._analyze_change()
                        time.sleep(self.cooldown)
                
                self.last_img = img_small
                time.sleep(15) # Checa a cada 15s (antes 10s)
                
            except Exception as e:
                print(f"Delta-Vision Erro: {e}")
                time.sleep(10)

    def _analyze_change(self):
        """Usa o Qwen2-VL com prompt ultra-conservador."""
        prompt = (
            "Aja como um observador silencioso. Procure EXCLUSIVAMENTE por ERROS CRÍTICOS DO SISTEMA "
            "ou FALHAS DE COMPILAÇÃO (textos em vermelho com 'Error', 'Exception' ou 'Crash'). "
            "Ignore qualquer outra mudança, como aberturas de sites, terminal, chat ou pastas. "
            "Se NÃO houver um ERRO FATAL visível, responda 'SKIP'. "
            "NUNCA liste o que está na tela se não for um erro."
        )
        
        description = self.vision.describe_screen(prompt)
        
        # Só fala se for realmente importante e não for delírio
        if description and "SKIP" not in description.upper() and len(description) < 150:
            # Mostra no HUD mas fica em SILÊNCIO na voz para não estressar
            self.hud.display_signal.emit(f"POSSÍVEL ERRO: {description[:50]}...", "PROACTIVE", 5000)
            # Desativado voice.speak para proatividade visual para evitar spam auditivo
            # self.voice.speak(f"Senhor, parece haver um erro: {description}")
            print(f"Delta-Vision detectou: {description}")

# Instância global gerenciada pelo MainApp
