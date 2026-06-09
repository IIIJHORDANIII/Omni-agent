import time
import os
from core.vision_service import VisionService
from core.system_monitor import SystemMonitor
from core.execution_service import ExecutionService

class VigiaService:
    """
    Protocolo VIGIA: Monitora ferramentas de design e gera documentação automática.
    """
    DESIGN_APPS = ["Figma", "Excalidraw", "Miro", "Adobe XD", "Sketch"]
    DOCS_DIR = "docs/architecture"

    def __init__(self, llm_manager):
        self.vision = VisionService()
        self.llm = llm_manager
        self.is_monitoring = False

    def start_vigilance(self):
        """Inicia o monitoramento proativo."""
        self.is_monitoring = True
        print("Protocolo VIGIA: Vigilância ativada.")
        
    def check_and_document(self):
        """Verifica se deve documentar o que está na tela."""
        active_app = SystemMonitor.get_active_app().get("active_app_name", "")
        
        if any(app.lower() in active_app.lower() for app in self.DESIGN_APPS):
            print(f"VIGIA: Detectado app de design ({active_app}). Analisando...")
            self._generate_architecture_doc()

    def _generate_architecture_doc(self):
        """Captura a tela, descreve a arquitetura e salva."""
        description = self.vision.describe_screen("Analise este diagrama de arquitetura ou design. Identifique componentes, fluxos e tecnologias mencionadas.")
        
        if "Erro" in description: return

        prompt = f"""Você é o JARVIS (Protocolo VIGIA).
Com base na análise visual abaixo, gere uma documentação técnica em Markdown.

ANÁLISE VISUAL:
{description}

ESTRUTURA DO DOC:
1. Título do Design.
2. Descrição Técnica.
3. Componentes Identificados.
4. Sugestões de Implementação.
"""
        doc_content = self.llm.generate_command(prompt, system_context="ARCHITECTURE_VIGILANCE")
        
        os.makedirs(self.DOCS_DIR, exist_ok=True)
        filename = f"arch_{int(time.time())}.md"
        path = os.path.join(self.DOCS_DIR, filename)
        
        with open(path, "w") as f:
            f.write(doc_content)
            
        print(f"VIGIA: Documentação salva em {path}")
        return path
