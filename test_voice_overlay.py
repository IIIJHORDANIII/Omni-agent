import sys
sys.path.append('src')

from PyQt6.QtWidgets import QApplication
from ui.hud import HUDOverlay
from ui.voice_overlay import VoiceOverlay
import math, time

app = QApplication(sys.argv)

hud = HUDOverlay()
hud.update_hud("Sistemas operacionais", "IDLE", 0)

voice = VoiceOverlay()
voice.set_state("listening")
voice.show()

for i in range(300):
    amp = (math.sin(i * 0.15) + 1) / 2 * 0.85
    voice.set_amplitude(amp)
    app.processEvents()
    time.sleep(0.03)

voice.set_state("idle")
hud.update_hud("Pronto", "IDLE", 0)
app.processEvents()
time.sleep(2)

sys.exit(0)
