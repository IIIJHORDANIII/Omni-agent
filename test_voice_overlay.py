import sys
sys.path.append('src')

from PyQt6.QtWidgets import QApplication
from ui.voice_overlay import VoiceOverlay
import time

app = QApplication(sys.argv)

overlay = VoiceOverlay()
overlay.set_state("listening")
overlay.show()

# Simula amplitude variando
import math
for i in range(200):
    amp = (math.sin(i * 0.2) + 1) / 2 * 0.8
    overlay.set_amplitude(amp)
    app.processEvents()
    time.sleep(0.05)

overlay.set_state("idle")
time.sleep(2)

sys.exit(0)
