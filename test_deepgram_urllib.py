import pyaudio
import numpy as np
import os
import io
import wave
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.config/anders/.env"))

def _audio_to_wav_bytes(audio_np, rate=16000):
    int16_data = (audio_np * 32767).astype("int16")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(int16_data.tobytes())
    return buf.getvalue()

def transcribe_wav_bytes(wav_bytes: bytes, language: str = "pt-BR") -> str:
    token = os.getenv("DEEPGRAM_API_KEY")
    url = f"https://api.deepgram.com/v1/listen?language={language}&model=nova-2&punctuate=true"
    req = urllib.request.Request(url, data=wav_bytes, method="POST")
    req.add_header("Authorization", f"Token {token}")
    req.add_header("Content-Type", "audio/wav")

    print("Sending to deepgram...")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result_data = response.read()
            if response.status != 200:
                print("Error from deepgram:", response.status)
                return ""
            result = json.loads(result_data)
            return result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "").strip()
    except Exception as e:
        print("Exception in deepgram:", e)
        return ""

p = pyaudio.PyAudio()
print("Recording 2 seconds...")
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
frames = []
for _ in range(0, int(16000 / 1024 * 2)):
    data = stream.read(1024, exception_on_overflow=False)
    frames.append(data)
stream.close()
p.terminate()

audio_data = b"".join(frames)
audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
wav_bytes = _audio_to_wav_bytes(audio_np)
res = transcribe_wav_bytes(wav_bytes)
print(f"Result: '{res}'")
