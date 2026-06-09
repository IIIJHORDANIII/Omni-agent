import os
import sys
import json
import time

sys.path.append(os.path.join(os.getcwd(), "src"))

from core.llm_client import LLMClient
from core.vision_service import VisionService
from core.execution_service import ExecutionService
from core.tool_dispatcher import ToolDispatcher

def test_full_workflow():
    print("=== INICIANDO TESTE DE FLUXO END-TO-END (OMNISCIENTE) ===")
    print("Objetivo: Ver a tela -> Processar Contexto -> Criar uma Nota com o resumo.\n")
    
    client = LLMClient()
    
    # 1. Simular uma pergunta que exige visão e ação
    prompt = "Descreva o que você está vendo na minha tela e salve isso em uma nova nota chamada 'Resumo da Tela'."
    
    print(f"PASSOS 1 & 2: Capturando visão e enviando para o Cérebro LLM...")
    # O chat(..., include_vision=True) faz exatamente o fluxo: Vision -> LLM -> Dispatcher
    response = client.chat([{"role": "user", "content": prompt}], include_vision=True)
    
    print(f"\n--- RESPOSTA FINAL DO AGENTE ---")
    print(response)
    print("\n--- FIM DO TESTE ---")

if __name__ == "__main__":
    test_full_workflow()
