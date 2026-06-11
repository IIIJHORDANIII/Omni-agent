import os
import time
import subprocess

class ImageGenerator:
    """
    Gerador de Imagens via Flux (MLX).
    Requer: pip install mflux
    """
    @staticmethod
    def generate_image(prompt, output_path=None):
        """Gera uma imagem usando Flux (via mflux) nativo para MLX."""
        if not output_path:
            output_path = os.path.expanduser(f"~/Desktop/generated_image_{int(time.time())}.png")
        
        # Usamos o mflux-generate com o modelo 'schnell' (4 steps) e quantização de 4-bit para ser leve
        # O mflux baixa o modelo automaticamente no primeiro uso.
        venv_bin = os.path.join(os.getcwd(), "venv", "bin", "mflux-generate")
        if not os.path.exists(venv_bin):
            venv_bin = "mflux-generate" # Fallback para o PATH
            
        cmd = f"{venv_bin} --model schnell --prompt '{prompt}' --output '{output_path}' --steps 4 --quantize 4"
        
        try:
            print(f"🎨 Gerando imagem localmente (Flux Schnell 4-bit): '{prompt}'...")
            # Aumentamos o timeout para o download do modelo no primeiro uso
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                # Tenta abrir a imagem gerada
                subprocess.run(["open", output_path])
                return f"Imagem gerada com sucesso e salva em: {output_path}"
            else:
                return f"Erro ao gerar imagem: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "A geração demorou demais (provavelmente baixando o modelo). Tente novamente em instantes."
        except Exception as e:
            return f"Falha na geração de imagem: {e}"
