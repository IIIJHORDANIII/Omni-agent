import os
import sys
import json
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.execution_service import ExecutionService
from core.tool_dispatcher import ToolDispatcher
from core.llm_manager import LLMManager

def run_test(name, action):
    print(f"--- TESTE: {name} ---")
    try:
        result = action()
        print(f"RESULTADO: {result}")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        return False

def main():
    print("=== INICIANDO DIAGNÓSTICO COMPREENSIVO DO AGENTE ===\n")
    
    results = {}

    # 1. Teste de Calendário (Melhorado)
    results["Calendário"] = run_test("Listar Eventos de Hoje", 
                                     lambda: ExecutionService.get_calendar_events())

    # 2. Teste de Lembretes (Novo)
    results["Lembretes"] = run_test("Listar Lembretes Pendentes", 
                                    lambda: ExecutionService.get_reminders())

    # 3. Teste de Sistema
    results["Info Sistema"] = run_test("Obter Info de Bateria/Disco", 
                                       lambda: ExecutionService.get_system_info())

    # 4. Teste de Arquivos
    test_file = "test_diagnostic.txt"
    results["Arquivos (Criar)"] = run_test("Criar Arquivo de Teste", 
                                           lambda: ExecutionService.create_file(test_file, "Conteúdo de diagnóstico"))
    results["Arquivos (Listar)"] = run_test("Listar Arquivos", 
                                            lambda: ExecutionService.list_files("."))
    results["Arquivos (Ler)"] = run_test("Ler Arquivo de Teste", 
                                         lambda: ExecutionService.read_file(test_file))
    
    # 5. Teste de Notas (AppleScript)
    results["Notas (Busca)"] = run_test("Buscar Notas (Query: 'IA')", 
                                        lambda: ExecutionService.notes_search("IA"))

    # 6. Teste de ToolDispatcher (Integração)
    # Testa se o dispatcher agora reconhece os comandos de calendário corretamente
    test_json = '[{"tool": "get_calendar_events", "params": {}}]'
    results["Dispatcher (Integração)"] = run_test("ToolDispatcher: get_calendar_events", 
                                                  lambda: ToolDispatcher.dispatch(test_json))

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

    print("\n=== RESUMO DO DIAGNÓSTICO ===")
    for test, status in results.items():
        print(f"{'[OK]' if status else '[FALHA]'} {test}")

if __name__ == "__main__":
    main()
