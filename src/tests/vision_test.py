import os
import sys

sys.path.append(os.path.join(os.getcwd(), "src"))

from core.vision_service import VisionService

def test_inference():
    print("Testando captura e inferência do Vision Service...")
    vs = VisionService()
    try:
        resultado = vs.describe_screen()
        print(f"\nRESULTADO DA VISÃO:\n{resultado}")
    except Exception as e:
        print(f"\nERRO NA INFERÊNCIA:\n{e}")

if __name__ == "__main__":
    test_inference()
