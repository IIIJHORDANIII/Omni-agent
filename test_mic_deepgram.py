import pyaudio
import numpy as np
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.config/anders/.env"))

import io
import wave
import requests

def _audio_to_wav_bytes(audio_np, rate=16000):
    int16_data = (audio_np * 32767).astype("int16")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(int16_data.tobytes())
    return buf.getvalue()

DEEPGRAM_ENDPOINT = "https://api.deepgram.com/v1/listen"
def transcribe_wav_bytes(wav_bytes: bytes, language: str = "pt-BR") -> str:
    token = os.getenv("DEEPGRAM_API_KEY")
    if not token:
        return "ERROR: No token"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "audio/wav",
    }
    params = {
        "language": language,
        "model": "nova-2",  # changed from general to nova-2 just in case
        "punctuate": "true",
    }
    response = requests.post(DEEPGRAM_ENDPOINT, headers=headers, params=params, data=wav_bytes)
    if response.status_code != 200:
        return f"API ERROR {response.status_code}: {response.text}"
    result = response.json()
    try:
        return result["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except Exception:
        return ""

p = pyaudio.PyAudio()
print("Recording 3 seconds...")
try:
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    frames = []
    for _ in range(0, int(16000 / 1024 * 3)):
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(data)
    stream.close()
    p.terminate()
    print("Done recording. Converting...")
    audio_data = b"".join(frames)
    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
    wav_bytes = _audio_to_wav_bytes(audio_np)
    print("Sending to Deepgram...")
    res = transcribe_wav_bytes(wav_bytes)
    print(f"Deepgram output: '{res}'")
except Exception as e:
    print(f"Error: {e}")
