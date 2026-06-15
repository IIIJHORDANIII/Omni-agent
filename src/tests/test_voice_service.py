import pytest
import subprocess
from unittest.mock import patch, MagicMock
from core.voice_service import VoiceService

@pytest.fixture
def voice_service():
    with patch("core.kokoro_service.KokoroService") as mock_kokoro:
        mock_kokoro.return_value.kokoro = None # Disable kokoro for this test
        service = VoiceService()
        return service

def test_stop_speaking(voice_service):
    with patch("subprocess.run") as mock_run:
        voice_service.stop_speaking()
        # Should call killall say
        mock_run.assert_called_with(["killall", "say"], capture_output=True)

def test_speak_native(voice_service):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        voice_service.speak("Olá mundo")
        
        # We need to wait a bit for the thread to start
        import time
        time.sleep(0.1)
        
        mock_popen.assert_called()
        assert "say" in mock_popen.call_args[0][0]
