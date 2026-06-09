import os
import subprocess
from core.execution_service import ExecutionService

class MediaEditor:
    """
    Editor de Mídia via FFmpeg comandado por voz.
    """
    @staticmethod
    def process(command):
        """Executa um comando ffmpeg baseado em descrição natural."""
        # Esta ferramenta será expandida via Protocolo Gênesis quando o usuário pedir algo específico.
        # Por padrão, fornecemos os comandos básicos.
        pass

    @staticmethod
    def cut_video(input_path, start_time, duration, output_path=None):
        """Corta um vídeo: ffmpeg -i input.mp4 -ss 00:00:10 -t 00:00:20 -c copy output.mp4"""
        if not output_path:
            name, ext = os.path.splitext(input_path)
            output_path = f"{name}_cut{ext}"
        
        cmd = f"ffmpeg -i '{input_path}' -ss {start_time} -t {duration} -c copy '{output_path}'"
        return ExecutionService.run_terminal_command(cmd)

    @staticmethod
    def convert_to_mp3(input_path, output_path=None):
        """Converte vídeo/áudio para MP3."""
        if not output_path:
            name, _ = os.path.splitext(input_path)
            output_path = f"{name}.mp3"
        
        cmd = f"ffmpeg -i '{input_path}' -q:a 0 -map a '{output_path}'"
        return ExecutionService.run_terminal_command(cmd)
