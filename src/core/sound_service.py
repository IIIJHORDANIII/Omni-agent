import subprocess
import os

class SoundService:
    @staticmethod
    def play_system_sound(name="Ping"):
        """Reproduz um som do sistema macOS."""
        sound_path = f"/System/Library/Sounds/{name}.aiff"
        if os.path.exists(sound_path):
            subprocess.Popen(["afplay", sound_path])
        else:
            print(f"Som não encontrado: {name}")

    @staticmethod
    def beep():
        SoundService.play_system_sound("Tink")

    @staticmethod
    def notify():
        SoundService.play_system_sound("Glass")

    @staticmethod
    def wake():
        SoundService.play_system_sound("Ping")

    @staticmethod
    def play_voice_start():
        """Som 'PAM' indicando início da gravação."""
        SoundService.play_system_sound("Hero")

    @staticmethod
    def success():
        """Som discreto de tarefa concluída."""
        SoundService.play_system_sound("Bottle")

    @staticmethod
    def paper():
        """Som tátil para criação de notas."""
        SoundService.play_system_sound("Pop")

    @staticmethod
    def digital_open():
        """Som de interface para abertura de apps."""
        SoundService.play_system_sound("Blow")
