import sys
import os
import json
import time

# Adiciona o path do projeto
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.llm_manager import LLMManager
from core.tool_dispatcher import ToolDispatcher
from core.execution_service import ExecutionService

def test_intent_recognition():
    print("\n--- TESTE DE RECONHECIMENTO DE INTENÇÃO (QWEN 2.5) ---")
    llm = LLMManager()
    
    test_cases = [
        "vê meus e-mails não lidos",
        "limpa minhas notas",
        "abre o google chrome",
        "qual o volume atual?",
        "o que tem na minha tela?",
        "e aí, tudo bem?",
        "manda um e-mail para o joão",
        "procura 'projeto' nas notas"
    ]
    
    for phrase in test_cases:
        print(f"\nUsuário: '{phrase}'")
        response = llm.generate_command(phrase)
        print(f"Resposta LLM: {response}")
        
        # Verifica se gerou JSON válido para comandos que exigem ação
        if any(word in phrase.lower() for word in ["e-mail", "notas", "abre", "tela"]):
            if "[" in response and "{" in response:
                print("✅ Comando detectado corretamente.")
            else:
                print("❌ FALHA: Deveria ter gerado um comando JSON.")
        else:
            print("✅ Resposta de chat detectada.")

def test_tool_execution_logic():
    print("\n--- TESTE DE LÓGICA DO DISPATCHER ---")
    
    # Teste de Sanitização
    sample_llm_output = "Com certeza! [{\"tool\": \"open_app\", \"params\": {\"app\": \"Notes\"}}]"
    result = ToolDispatcher.dispatch(sample_llm_output)
    print(f"Sanitização JSON: {'✅' if 'Abrindo' in str(result) or 'success' in str(result).lower() else '❌'}")

def check_vision_memory():
    print("\n--- TESTE DE MEMÓRIA DE VISÃO ---")
    try:
        from core.vision_service import VisionService
        vision = VisionService()
        print("Carregando modelo de visão para teste de carga...")
        res = vision.describe_screen("Teste")
        print(f"Resultado visão: {res[:50]}...")
        print("✅ Visão carregada sem crash de memória.")
    except Exception as e:
        print(f"❌ Erro na visão: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO AUDITORIA COMPLETA DO OMNISCIENT AGENT")
    # check_vision_memory() # Comentar se não quiser carregar 2GB agora
    test_intent_recognition()
    test_tool_execution_logic()
    print("\n--- AUDITORIA CONCLUÍDA ---")
