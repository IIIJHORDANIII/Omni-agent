import threading
import time
import os
import numpy as np
from PIL import Image, ImageChops
from core.vision_service import VisionService

class DeltaVisionService:
    def __init__(self, voice_service, hud):
        self.vision_enabled = os.getenv("VISION_ENABLED", "true").lower() in ("true", "1", "yes")
        if self.vision_enabled:
            self.vision = VisionService()
        else:
            self.vision = None
        self.voice = voice_service
        self.hud = hud
        self.last_img = None
        self.running = False
        self.cooldown = 60
        self.sensitivity = 60

    def start(self):
        if not self.vision_enabled:
            print("Delta-Vision: DESABILITADO (VISION_ENABLED=false).")
            return
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        print("Delta-Vision: Monitoramento proativo ativado (Modo Silencioso).")

    def _monitor_loop(self):
        while self.running:
            try:
                with VisionService._lock:
                    img = self.vision.capture_screen_pil()
                if img is None:
                    time.sleep(10)
                    continue

                img_small = img.resize((256, 256)).convert("L")

                if self.last_img:
                    diff = ImageChops.difference(img_small, self.last_img)
                    stat = np.array(diff).mean()

                    if stat > self.sensitivity:
                        print(f"Delta-Vision: Mudança detectada ({stat:.2f}).")
                        self._analyze_change()
                        time.sleep(self.cooldown)

                self.last_img = img_small
                time.sleep(15)

            except Exception as e:
                print(f"Delta-Vision Erro: {e}")
                time.sleep(10)

    def _analyze_change(self):
        prompt = (
            "Aja como um observador silencioso. Procure EXCLUSIVAMENTE por ERROS CRÍTICOS DO SISTEMA "
            "ou FALHAS DE COMPILAÇÃO (textos em vermelho com 'Error', 'Exception' ou 'Crash'). "
            "Ignore qualquer outra mudança, como aberturas de sites, terminal, chat ou pastas. "
            "Se NÃO houver um ERRO FATAL visível, responda 'SKIP'. "
            "NUNCA liste o que está na tela se não for um erro."
        )

        description = self.vision.describe_screen(prompt)

        if description and "SKIP" not in description.upper() and len(description) < 150:
            self.hud.display_signal.emit(f"POSSÍVEL ERRO: {description[:50]}...", "PROACTIVE", 5000)
            print(f"Delta-Vision detectou: {description}")