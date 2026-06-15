import os
import threading
from core.execution_service import ExecutionService
from core.semantic_memory import SemanticMemory

class ProjectCrawlerService:
    """
    Serviço que mapeia exaustivamente as pastas de projeto e indexa na memória semântica.
    Focado em ~/Documents/pessoal e ~/Documents/payjota.
    """
    def __init__(self, llm_manager):
        self.llm = llm_manager
        self.semantic_memory = SemanticMemory()
        self.base_paths = [
            os.path.expanduser("~/Documents/pessoal"),
            os.path.expanduser("~/Documents/payjota")
        ]

    def start_background_crawl(self):
        """Dispara o mapeamento em uma thread separada para não travar o app."""
        threading.Thread(target=self.run_crawl, daemon=True).start()

    def run_crawl(self):
        print("🔍 Crawler: Iniciando mapeamento profundo dos projetos...")
        for base in self.base_paths:
            if not os.path.exists(base): continue
            
            try:
                # Lista subpastas (projetos)
                projects = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
                for project in projects:
                    path = os.path.join(base, project)
                    if ".git" in os.listdir(path) or "package.json" in os.listdir(path) or "venv" in os.listdir(path):
                        self._index_project(project, path)
            except Exception as e:
                print(f"Erro ao acessar base {base}: {e}")
        
        print("✅ Crawler: Mapeamento concluído e indexado na Memória Semântica.")

    def _index_project(self, name, path):
        """Extrai o DNA do projeto e salva na memória vetorial."""
        print(f"🔍 Crawler: Mapeando DNA de {name}...")
        
        # 1. Coleta arquivos chave para o resumo
        key_files = []
        for f in ["README.md", "package.json", "requirements.txt", "docker-compose.yml", "schema.prisma", "models.py"]:
            if os.path.exists(os.path.join(path, f)):
                key_files.append(f)
        
        # 2. Gera um resumo da árvore de arquivos (limitado)
        tree_res = ExecutionService.run_terminal_command(f"find '{path}' -maxdepth 2 -not -path '*/.*' | head -n 30")
        tree_str = tree_res.get("stdout", "")

        # 3. Usa a LLM para gerar um "DNA de Arquitetura"
        prompt = f"""Analise a estrutura do projeto '{name}' localizado em '{path}'.
        ARQUIVOS CHAVE ENCONTRADOS: {key_files}
        ESTRUTURA DE PASTAS:
        {tree_str}
        
        GERA UM DNA DO PROJETO (Max 200 palavras):
        - Qual a Stack principal?
        - Qual o propósito provável?
        - Liste as 3 principais pastas e o que elas fazem.
        """
        
        try:
            dna = self.llm.generate_command(prompt, system_context="PROJECT_CRAWLER")
            
            # 4. Salva na Memória Semântica
            self.semantic_memory.write(
                f"project_map_{name}", 
                f"Projeto: {name} | Caminho: {path}\nDNA: {dna}",
                metadata={"type": "project_map", "path": path}
            )
        except Exception as e:
            print(f"Erro ao indexar projeto {name}: {e}")
