import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.config/anders/.env"))
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.voice_service import VoiceService

def test():
    print("Iniciando VoiceService...")
    voice = VoiceService(use_remote=True)
    
    class DummyStream:
        def read(self, chunk_size, **kwargs):
            return b"\x00" * (chunk_size * 2)
        def stop_stream(self): pass
        def close(self): pass
        
    voice.stream = DummyStream()
    
    print("\n--- FALE ALGO AGORA ---")
    res = voice.listen(timeout=2)
    print(f"\nResultado Final: {res}")

if __name__ == "__main__":
    test()
