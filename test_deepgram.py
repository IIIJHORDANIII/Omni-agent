import os
from dotenv import load_dotenv
import numpy as np

load_dotenv(os.path.expanduser("~/.config/anders/.env"))

import sys
sys.path.append(os.path.abspath("src"))
from core.deepgram_transcriber import transcribe_wav_bytes
from core.voice_service import VoiceService

# Fake voice service just for wav conversion
class FakeVoice:
    RATE = 16000
    def _audio_to_wav_bytes(self, audio_np):
        import io
        import wave
        int16_data = (audio_np * 32767).astype("int16")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.RATE)
            wf.writeframes(int16_data.tobytes())
        return buf.getvalue()

fv = FakeVoice()
audio_np = np.zeros(16000, dtype=np.float32) # 1 sec of silence
wav_bytes = fv._audio_to_wav_bytes(audio_np)

print("Sending to deepgram...")
try:
    res = transcribe_wav_bytes(wav_bytes)
    print(f"Result: '{res}'")
except Exception as e:
    print(f"Error: {e}")
