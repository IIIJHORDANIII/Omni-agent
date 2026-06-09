import os
import sys

sys.path.append(os.path.join(os.getcwd(), "src"))

from core.ghost_programmer import GhostPairProgrammer
from core.llm_manager import LLMManager

def test_ghost():
    print("Iniciando GhostPairProgrammer test...")
    llm = LLMManager()
    ghost = GhostPairProgrammer(llm, None, None)
    
    # Simulate a bug fix request
    print("Pedindo para o Ghost investigar um problema fictício...")
    try:
        resultado = ghost.investigate_and_fix("A função _ensure_stream no llm_manager está causando problemas de concorrência.", mode="auto")
        print(f"\nRESULTADO GHOST:\n{resultado}")
    except Exception as e:
        print(f"\nERRO GHOST:\n{e}")

if __name__ == "__main__":
    test_ghost()
