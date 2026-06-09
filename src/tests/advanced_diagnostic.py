import os
import sys

sys.path.append(os.path.join(os.getcwd(), "src"))

from core.vision_service import VisionService
from core.linear_service import LinearService
from core.github_service import GithubService
from core.ghost_programmer import GhostPairProgrammer
from core.llm_manager import LLMManager

def run_test(name, action):
    print(f"\n--- TESTE: {name} ---")
    try:
        result = action()
        print(f"RESULTADO: {str(result)[:500]}...") # Truncate long outputs
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        return False

def test_vision():
    vs = VisionService()
    # Ensure model is loaded first to catch init errors
    vs._ensure_stream()
    vs._ensure_model_loaded()
    if vs.model is None:
        raise Exception("Modelo de visão falhou ao carregar.")
    return "Visão carregada com sucesso."

def test_linear():
    lin = LinearService()
    return lin.get_my_issues()

def test_github():
    gh = GithubService()
    # Test with a known or fallback behavior. If token is invalid, it will say so.
    # We just want to check if the service runs.
    return gh.get_pull_requests("test/repo")

def main():
    print("=== INICIANDO DIAGNÓSTICO AVANÇADO (VISION, LINEAR, GITHUB) ===")
    
    results = {}
    
    # 1. Linear
    results["Linear API"] = run_test("Conexão Linear", test_linear)
    
    # 2. GitHub
    results["GitHub API"] = run_test("Conexão GitHub", test_github)
    
    # 3. Vision
    results["Vision Service"] = run_test("Carregamento do Qwen2-VL", test_vision)

    print("\n=== RESUMO DO DIAGNÓSTICO AVANÇADO ===")
    for test, status in results.items():
        print(f"{'[OK]' if status else '[FALHA]'} {test}")

if __name__ == "__main__":
    main()
