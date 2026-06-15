import os
import time
import shutil
import hashlib
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class OrganizerHandler(FileSystemEventHandler):
    def __init__(self, watch_path, llm_client=None):
        self.watch_path = watch_path
        self.llm_client = llm_client
        self.last_check = 0
        self.cooldown = 3
        
        # Mapeamento completo de extensoes
        self.type_map = {
            "Documentos": ["pdf", "docx", "doc", "txt", "rtf", "odt", "pages", "key", "numbers", "csv", "xlsx", "xls", "pptx", "ppt"],
            "Imagens": ["jpg", "jpeg", "png", "svg", "webp", "gif", "bmp", "tiff", "ico", "heic", "heif"],
            "Videos": ["mp4", "mov", "avi", "mkv", "wmv", "flv", "webm", "m4v"],
            "Audio": ["mp3", "wav", "aac", "flac", "ogg", "m4a", "wma"],
            "Codigos": ["py", "js", "ts", "jsx", "tsx", "html", "css", "swift", "java", "c", "cpp", "go", "rs", "rb"],
            "Arquivos": ["zip", "gz", "tar", "rar", "7z", "xz"],
            "Executaveis": ["dmg", "pkg", "app", "deb", "rpm"],
            "Modelos_ML": ["safetensors", "gguf", "ggml", "bin", "onnx", "pt", "pth"],
            "Fontes": ["ttf", "otf", "woff", "woff2"],
        }
        
        # Tamanho maximo para analise LLM (evita processar arquivos enormes)
        self.MAX_LLM_SIZE_MB = 50

    def on_created(self, event):
        if event.is_directory: return
        if time.time() - self.last_check < self.cooldown: return
        self.last_check = time.time()
        self.organize_file(event.src_path)

    def organize_file(self, file_path):
        """Organiza um arquivo individual."""
        try:
            filename = os.path.basename(file_path)
            if filename.startswith(".") or filename.startswith("~$"): return
            
            # Verifica se o arquivo ainda existe (pode ter sido movido)
            if not os.path.exists(file_path): return
            
            ext = filename.split(".")[-1].lower() if "." in filename else ""
            
            # 1. Classificacao por extensao
            target_folder = "Outros"
            for folder, exts in self.type_map.items():
                if ext in exts:
                    target_folder = folder
                    break
            
            # 2. Classificacao por tamanho (arquivos enormes vao direto)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 500:
                target_folder = "Arquivos_Grandes"
            
            # 3. Classificacao LLM para documentos (opcional)
            if self.llm_client and target_folder in ("Documentos", "Outros") and size_mb < self.MAX_LLM_SIZE_MB:
                category = self._classify_with_llm(filename)
                if category:
                    target_folder = os.path.join(target_folder, category)
            
            # 4. Move o arquivo
            dest_dir = os.path.join(self.watch_path, "_Organizado", target_folder)
            os.makedirs(dest_dir, exist_ok=True)
            
            dest_path = os.path.join(dest_dir, filename)
            if os.path.exists(dest_path):
                name, extension = os.path.splitext(filename)
                dest_path = os.path.join(dest_dir, f"{name}_{int(time.time())}{extension}")
            
            shutil.move(file_path, dest_path)
            print(f"Auto-Organizer: {filename} -> {target_folder}")
            
        except Exception as e:
            print(f"Erro no Auto-Organizer: {e}")

    def _classify_with_llm(self, filename):
        """Usa LLM para classificar o arquivo em subcategorias."""
        try:
            prompt = f"Arquivo: '{filename}'. Categoria (1 palavra): Trabalho, Pessoal, Estudo, Financas, Governo, ou outro?"
            response = self.llm_client.manager.generate_command(prompt)
            category = response.strip().replace(".", "").split()[0] if response else ""
            if len(category) < 20 and category:
                return category
        except Exception:
            pass
        return None


class AdvancedOrganizer:
    """
    Organizador avancado com limpeza, deduplicacao e relatorios.
    """
    
    def __init__(self, watch_path=None):
        self.watch_path = watch_path or os.path.expanduser("~/Downloads")
        self.organized_path = os.path.join(self.watch_path, "_Organizado")

    def scan_duplicates(self, directory=None):
        """Encontra arquivos duplicados por hash."""
        target = directory or self.organized_path
        if not os.path.exists(target):
            return []
        
        hashes = {}
        duplicates = []
        
        for root, dirs, files in os.walk(target):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    file_hash = self._file_hash(filepath)
                    if file_hash in hashes:
                        duplicates.append({
                            "original": hashes[file_hash],
                            "duplicate": filepath,
                            "size_mb": round(os.path.getsize(filepath) / (1024*1024), 2)
                        })
                    else:
                        hashes[file_hash] = filepath
                except Exception:
                    pass
        
        return duplicates

    def cleanup_old_files(self, days=30, dry_run=True):
        """Remove ou lista arquivos antigos."""
        if not os.path.exists(self.organized_path):
            return []
        
        cutoff = datetime.now() - timedelta(days=days)
        old_files = []
        
        for root, dirs, files in os.walk(self.organized_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        size_mb = os.path.getsize(filepath) / (1024*1024)
                        old_files.append({
                            "path": filepath,
                            "name": filename,
                            "age_days": (datetime.now() - mtime).days,
                            "size_mb": round(size_mb, 2)
                        })
                        if not dry_run:
                            os.remove(filepath)
                except Exception:
                    pass
        
        return old_files

    def get_stats(self):
        """Retorna estatisticas da organizacao."""
        if not os.path.exists(self.organized_path):
            return {"organized": False, "message": "Pasta _Organizado nao existe ainda"}
        
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "by_folder": {},
            "by_extension": {}
        }
        
        for root, dirs, files in os.walk(self.organized_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    size = os.path.getsize(filepath)
                    ext = filename.split(".")[-1].lower() if "." in filename else "sem_ext"
                    rel_path = os.path.relpath(root, self.organized_path)
                    folder = rel_path.split(os.sep)[0] if rel_path != "." else "Raiz"
                    
                    stats["total_files"] += 1
                    stats["total_size_mb"] += size / (1024*1024)
                    
                    stats["by_folder"][folder] = stats["by_folder"].get(folder, 0) + 1
                    stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1
                except Exception:
                    pass
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        stats["organized"] = True
        return stats

    def organize_existing(self, directory=None):
        """Organiza arquivos existentes na pasta."""
        target = directory or self.watch_path
        if not os.path.exists(target):
            return "Diretorio nao encontrado."
        
        handler = OrganizerHandler(target)
        moved = 0
        
        for filename in os.listdir(target):
            filepath = os.path.join(target, filename)
            if os.path.isfile(filepath) and not filename.startswith("."):
                handler.organize_file(filepath)
                moved += 1
        
        return f"{moved} arquivos organizados."

    def search_files(self, query, directory=None):
        """Busca arquivos por nome."""
        target = directory or self.organized_path
        if not os.path.exists(target):
            return []
        
        results = []
        query_lower = query.lower()
        
        for root, dirs, files in os.walk(target):
            for filename in files:
                if query_lower in filename.lower():
                    filepath = os.path.join(root, filename)
                    results.append({
                        "name": filename,
                        "path": filepath,
                        "size_mb": round(os.path.getsize(filepath) / (1024*1024), 2)
                    })
        
        return results[:20]

    def _file_hash(self, filepath, chunk_size=8192):
        """Calcula hash MD5 de um arquivo."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()


class AutoOrganizerService:
    """Servico de monitoramento continuo com watchdog."""
    
    def __init__(self, llm_client=None, watch_path=None):
        self.watch_path = watch_path or os.path.expanduser("~/Downloads")
        self.llm_client = llm_client
        self.observer = Observer()
        self.advanced = AdvancedOrganizer(self.watch_path)

    def start(self, observer=None):
        """Inicia o monitoramento da pasta."""
        if not os.path.exists(self.watch_path): return
        
        handler = OrganizerHandler(self.watch_path, self.llm_client)
        self.observer.schedule(handler, self.watch_path, recursive=False)
        self.observer.start()
        print(f"Auto-Organizer: Monitorando {self.watch_path}")

    def stop(self):
        """Para o monitoramento."""
        self.observer.stop()
        self.observer.join()

    def scan_duplicates(self):
        """Encontra arquivos duplicados."""
        return self.advanced.scan_duplicates()

    def cleanup_old(self, days=30, dry_run=True):
        """Limpa arquivos antigos."""
        return self.advanced.cleanup_old_files(days, dry_run)

    def get_stats(self):
        """Retorna estatisticas."""
        return self.advanced.get_stats()

    def organize_all(self):
        """Organiza todos os arquivos existentes."""
        return self.advanced.organize_existing()

    def search(self, query):
        """Busca arquivos."""
        return self.advanced.search_files(query)
