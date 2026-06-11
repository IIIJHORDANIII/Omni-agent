import os
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core.llm_client import LLMClient

class OrganizerHandler(FileSystemEventHandler):
    def __init__(self, watch_path, llm_client):
        self.watch_path = watch_path
        self.llm_client = llm_client
        # Pastas base de organização
        self.base_folders = {
            "Documentos": ["pdf", "docx", "txt", "xlsx"],
            "Imagens": ["jpg", "jpeg", "png", "svg", "webp"],
            "Videos": ["mp4", "mov", "avi"],
            "Projetos": ["zip", "gz", "tar"],
            "Executáveis": ["dmg", "pkg"]
        }

    def on_created(self, event):
        if not event.is_directory:
            # Espera o arquivo ser finalizado
            time.sleep(2)
            self.organize_file(event.src_path)

    def organize_file(self, file_path):
        try:
            filename = os.path.basename(file_path)
            if filename.startswith("."): return

            print(f"Auto-Organizer: Analisando {filename}...")
            
            # 1. Tenta classificação rápida por extensão
            ext = filename.split(".")[-1].lower()
            target_folder = "Outros"
            
            for folder, exts in self.base_folders.items():
                if ext in exts:
                    target_folder = folder
                    break

            # 2. Se for documento ou imagem, usa IA para refinar a pasta
            if target_folder in ["Documentos", "Imagens"] or ext == "txt":
                prompt = f"Analise o nome do arquivo: '{filename}'. Para qual categoria ele pertence: [Trabalho, Pessoal, Estudo, Finanças, Governo]? Responda apenas uma palavra."
                category = self.llm_client.chat([{"role": "user", "content": prompt}])
                category = category.strip().replace(".", "")
                if len(category) < 20: # Evita respostas longas ou erros
                    target_folder = os.path.join(target_folder, category)

            # 3. Move o arquivo
            dest_dir = os.path.join(self.watch_path, target_folder)
            os.makedirs(dest_dir, exist_ok=True)
            
            dest_path = os.path.join(dest_dir, filename)
            # Evita sobrescrever
            if os.path.exists(dest_path):
                name, extension = os.path.splitext(filename)
                dest_path = os.path.join(dest_dir, f"{name}_{int(time.time())}{extension}")

            shutil.move(file_path, dest_path)
            print(f"Auto-Organizer: {filename} -> {target_folder}")
            
        except Exception as e:
            print(f"Erro no Auto-Organizer: {e}")

class AutoOrganizerService:
    def __init__(self, llm_client, watch_path=None):
        self.watch_path = watch_path or os.path.expanduser("~/Downloads")
        self.llm_client = llm_client
        self.observer = Observer()

    def start(self, observer=None):
        if not os.path.exists(self.watch_path): return
        handler = OrganizerHandler(self.watch_path, self.llm_client)
        
        if observer:
            self.observer = observer
            self.observer.schedule(handler, self.watch_path, recursive=False)
        else:
            self.observer = Observer()
            self.observer.schedule(handler, self.watch_path, recursive=False)
            self.observer.start()
            
        print(f"Auto-Organizer: Monitorando {self.watch_path}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
