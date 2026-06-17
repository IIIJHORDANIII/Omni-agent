import os
import time
import subprocess

class ImageGenerator:
    """
    Gerador de Imagens via MLX local.
    Requer: pip install mlx-image
    """
    @staticmethod
    def generate_image(prompt, output_path=None):
        """Gera uma imagem usando Stable Diffusion via MLX."""
        if not output_path:
            output_path = os.path.expanduser(f"~/Desktop/generated_image_{int(time.time())}.png")
        
        # O comando nativo do MLX Image para gerar imagens rápido no Mac
        # (Assumindo que mlx-image está instalado, faremos a chamada CLI por simplicidade e isolamento)
        cmd = f"python -m mlx_image.generate --prompt '{prompt}' --output '{output_path}' --steps 4" # Usando turbo (4 steps) para rapidez
        
        try:
            print(f"🎨 Gerando imagem localmente: '{prompt}'...")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                # Tenta abrir a imagem gerada para mostrar ao usuário
                subprocess.run(["open", output_path])
                return f"Imagem gerada e salva em: {output_path}"
            else:
                # Se não estiver instalado, instrui o agente a pedir para o usuário instalar
                if "No module named mlx_image" in result.stderr:
                    return "Erro: O pacote 'mlx-image' não está instalado. Execute 'pip install mlx-image' para ativar a geração de imagens."
                return f"Erro ao gerar imagem: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "A geração da imagem demorou muito e foi cancelada."
        except Exception as e:
            return f"Falha na geração de imagem: {e}"
