import os
import requests

DEEPGRAM_ENDPOINT = "https://api.deepgram.com/v1/listen"

def transcribe_wav_bytes(wav_bytes: bytes, language: str = "pt-BR") -> str:
    """Send raw WAV audio bytes to Deepgram and return the transcription.

    The function expects a standard PCM WAV (16‑bit, 16 kHz, mono) which is the
    format produced by the audio collector in ``VoiceService``.
    """
    import subprocess
    import json
    import tempfile

    token = os.getenv("DEEPGRAM_API_KEY")
    if not token:
        raise RuntimeError("DEEPGRAM_API_KEY environment variable not set")

    url = f"{DEEPGRAM_ENDPOINT}?language={language}&model=nova-2&punctuate=true&smart_format=true&diarize=false"
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp_path = f.name

    try:
        cmd = [
            "curl", "-s", "-X", "POST", url,
            "-H", f"Authorization: Token {token}",
            "-H", "Content-Type: audio/wav",
            "--data-binary", f"@{tmp_path}",
            "--max-time", "10"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if result.returncode != 0:
            print(f"Deepgram curl failed: {result.stderr}")
            return ""
            
        data = json.loads(result.stdout)
        return data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "").strip()
    except Exception as e:
        print(f"Deepgram erro inesperado: {e}")
        return ""
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass
