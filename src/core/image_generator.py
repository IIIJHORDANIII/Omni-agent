import os
import time
import requests

class ImageGenerator:
    """
    Gerador de Imagens Leve (Cloud-based).
    Gera imagens usando a API do Hugging Face (requer token pré-configurado).
    """
    @staticmethod
    def preload_model(hud=None):
        pass

    @staticmethod
    def generate_image(prompt, output_path=None):
        """Gera uma imagem via Hugging Face Inference API."""
        if not output_path:
            output_path = os.path.expanduser(f"~/Desktop/generated_image_{int(time.time())}.png")
        
        try:
            print(f"🎨 Gerando imagem via Hugging Face API: '{prompt}'...")
            
            # Tenta ler o token salvo pelo 'huggingface-cli login'
            token_path = os.path.expanduser("~/.cache/huggingface/token")
            if not os.path.exists(token_path):
                return "Erro: Token do Hugging Face não encontrado. Por favor, faça login com 'huggingface-cli login'."
                
            with open(token_path, "r") as f:
                token = f.read().strip()
                
            API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"inputs": prompt}
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # Abre a imagem no Mac
                import subprocess
                subprocess.run(["open", output_path])
                return f"Imagem gerada com sucesso e salva em: {output_path}"
            else:
                return f"Erro na API do Hugging Face (Status {response.status_code}): {response.text}"
                
        except Exception as e:
            return f"Falha na geração de imagem: {e}"
