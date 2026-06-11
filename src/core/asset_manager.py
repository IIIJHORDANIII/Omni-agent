import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image
from core.execution_service import ExecutionService

class AssetHandler(FileSystemEventHandler):
    def __init__(self, target_project_path=None):
        self.target_project_path = target_project_path or os.getcwd()
        self.extensions = ('.png', '.jpg', '.jpeg', '.webp')

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(self.extensions):
            # Pequeno delay para garantir que o arquivo foi totalmente salvo (ex: export do Figma)
            time.sleep(1)
            self.process_image(event.src_path)

    def process_image(self, file_path):
        try:
            filename = os.path.basename(file_path)
            name, _ = os.path.splitext(filename)
            
            # 1. Define destino (Tenta achar uma pasta de assets no projeto atual)
            # Se não achar, usa o diretório raiz
            potential_assets = [
                os.path.join(self.target_project_path, "public/assets"),
                os.path.join(self.target_project_path, "src/assets"),
                os.path.join(self.target_project_path, "assets")
            ]
            
            dest_dir = self.target_project_path
            for d in potential_assets:
                if os.path.exists(d):
                    dest_dir = d
                    break
            
            dest_path = os.path.join(dest_dir, f"{name}.webp")
            
            # 2. Otimiza e Converte para WebP
            print(f"JARVIS Forge: Otimizando asset {filename}...")
            with Image.open(file_path) as img:
                img.save(dest_path, "webp", quality=80)
            
            print(f"JARVIS Forge: Asset salvo em {dest_path}")
            # Opcional: Remover o original (comentado por segurança)
            # os.remove(file_path)
            
        except Exception as e:
            print(f"Erro ao processar asset: {e}")

class AssetManagerService:
    def __init__(self, watch_paths=None):
        # Por padrão observa Desktop e Downloads
        self.watch_paths = watch_paths or [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads")
        ]
        self.observer = Observer()

    def start(self, observer=None):
        handler = AssetHandler()
        if observer:
            self.observer = observer
            is_external = True
        else:
            self.observer = Observer()
            is_external = False

        for path in self.watch_paths:
            if os.path.exists(path):
                self.observer.schedule(handler, path, recursive=False)
                print(f"Forge: Monitorando assets em {path}")
        
        if not is_external:
            self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
