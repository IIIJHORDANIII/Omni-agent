import pyaudio
import numpy as np

p = pyaudio.PyAudio()
default_input = p.get_default_input_device_info()
print(f"Default Input Device: {default_input['name']}")

try:
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    data = stream.read(1024, exception_on_overflow=False)
    audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    energy = np.sqrt(np.mean(audio_np**2))
    print(f"Successfully read chunk. Energy: {energy}")
    stream.close()
except Exception as e:
    print(f"Error reading: {e}")
p.terminate()
