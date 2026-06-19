import sys, os
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.config/anders/.env"))
sys.path.append(os.path.join(os.getcwd(), "src"))
from core.voice_service import VoiceService
import numpy as np

def test():
    print("Creating voice service...")
    v = VoiceService(use_remote=True)
    fake_audio = [0.0] * 16000 * 2  
    wav_bytes = v._audio_to_wav_bytes(np.array(fake_audio, dtype=np.float32))
    
    from core.deepgram_transcriber import transcribe_wav_bytes
    print("Calling transcribe_wav_bytes with curl...")
    res = transcribe_wav_bytes(wav_bytes, language="pt-BR")
    print("Deepgram Result:", repr(res))

if __name__ == "__main__":
    test()
