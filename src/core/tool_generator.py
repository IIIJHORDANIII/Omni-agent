import os
import sys
from core.execution_service import ExecutionService

class ToolGenerator:
    """
    Protocolo Gênesis: Permite que o JARVIS crie suas próprias ferramentas Python e UIs.
    """
    CUSTOM_TOOLS_DIR = "src/tools/generated"

    @staticmethod
    def generate_and_execute(llm_manager, requirement):
        """O JARVIS escreve um script para resolver um problema novo e o executa."""
        is_ui = "interface" in requirement.lower() or "ui" in requirement.lower() or "janela" in requirement.lower()
        
        print(f"Gênesis: Criando {'interface' if is_ui else 'ferramenta'} para: {requirement}")
        
        ui_prompt = """
Você deve criar uma interface PyQt6 completa e autônoma.
REGRAS PARA UI:
1. Use QWidget ou QMainWindow.
2. Inclua todo o código necessário (imports, classe e execução 'if __name__ == "__main__"').
3. Estilo: Use stylesheets para um visual dark/futurista (estilo JARVIS).
4. A janela deve ser pequena e focada na tarefa.
"""
        
        prompt = f"""Você é o JARVIS em modo Gênesis.
O usuário precisa de uma funcionalidade que você ainda não tem: "{requirement}".

SUA TAREFA:
1. Escreva um script Python autônomo e seguro para realizar esta tarefa no macOS.
2. Use bibliotecas padrão ou as já instaladas (PyQt6, psutil, Pillow, pyperclip, requests).
{ui_prompt if is_ui else ""}
3. O script deve ser modular e retornar um resultado claro.

REGRAS:
- Responda APENAS com o código Python.
- Sem explicações ou comentários fora do código.
"""
        code = llm_manager.generate_command(prompt, system_context="GENESIS_TOOL_CREATION").strip()
        
        # Nome único baseado no requisito
        tool_name = requirement.lower().replace(" ", "_")[:20] + (".py" if not is_ui else "_ui.py")
        os.makedirs(ToolGenerator.CUSTOM_TOOLS_DIR, exist_ok=True)
        path = os.path.join(ToolGenerator.CUSTOM_TOOLS_DIR, tool_name)
        
        # Salva
        with open(path, "w") as f:
            f.write(code)
            
        print(f"Gênesis: {'Lançando UI' if is_ui else 'Executando ferramenta'} {tool_name}...")
        
        if is_ui:
            # Lança como um processo separado para não travar o agente principal
            import subprocess
            subprocess.Popen([sys.executable, path], start_new_session=True)
            return {"status": "success", "tool_path": path, "output": "UI lançada em segundo plano."}
        else:
            result = ExecutionService.execute_python(code)
            return {"status": "success", "tool_path": path, "output": result}
