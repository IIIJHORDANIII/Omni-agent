import os
import subprocess
from core.execution_service import ExecutionService

class MediaEditor:
    """
    Editor de Mídia via FFmpeg comandado por voz.
    """
    
    @staticmethod
    def _check_ffmpeg():
        """Verifica se o ffmpeg está instalado."""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def process(command):
        """Executa um comando ffmpeg baseado em descrição natural."""
        if not MediaEditor._check_ffmpeg():
            return "FFmpeg não está instalado. Instale via: brew install ffmpeg"
        return ExecutionService.run_terminal_command(f"ffmpeg {command}")

    @staticmethod
    def cut_video(input_path, start_time, duration, output_path=None):
        """Corta um vídeo."""
        if not MediaEditor._check_ffmpeg():
            return "FFmpeg não está instalado."
        if not output_path:
            name, ext = os.path.splitext(input_path)
            output_path = f"{name}_cut{ext}"
        
        cmd = f"ffmpeg -i '{input_path}' -ss {start_time} -t {duration} -c copy '{output_path}'"
        return ExecutionService.run_terminal_command(cmd)

    @staticmethod
    def convert_to_mp3(input_path, output_path=None):
        """Converte vídeo/áudio para MP3."""
        if not MediaEditor._check_ffmpeg():
            return "FFmpeg não está instalado."
        if not output_path:
            name, _ = os.path.splitext(input_path)
            output_path = f"{name}.mp3"
        
        cmd = f"ffmpeg -i '{input_path}' -q:a 0 -map a '{output_path}'"
        return ExecutionService.run_terminal_command(cmd)

    @staticmethod
    def get_media_info(input_path):
        """Retorna informações sobre um arquivo de mídia."""
        if not MediaEditor._check_ffmpeg():
            return "FFmpeg não está instalado."
        cmd = f"ffprobe -v quiet -print_format json -show_format -show_streams '{input_path}'"
        return ExecutionService.run_terminal_command(cmd)
