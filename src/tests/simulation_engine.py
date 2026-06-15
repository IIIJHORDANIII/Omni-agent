import time
import os
import subprocess
import threading

class SimulationEngine:
    """
    Simula eventos reais do Mac para testar a proatividade do Agente.
    Ex: Injeção de erros em logs, falhas de comando, etc.
    """
    
    @staticmethod
    def simulate_terminal_error(command="npm run build"):
        """Injeta um erro no socket do Terminal Overwatch."""
        import socket
        import json
        
        payload = {
            "command": command,
            "exit_code": 1,
            "stderr": "Error: compilation failed at line 42"
        }
        
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("127.0.0.1", 9999))
            client.sendall(json.dumps(payload).encode('utf-8'))
            client.close()
            return "Erro de terminal simulado e enviado."
        except Exception as e:
            return f"Falha na simulação: {e}"

    @staticmethod
    def simulate_log_error(log_path="/tmp/test_app.log", message="CRITICAL: Database connection lost"):
        """Escreve um erro em um arquivo de log monitorado."""
        with open(log_path, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
        return f"Log de erro injetado em {log_path}"

    @staticmethod
    def run_full_simulation():
        print("--- INICIANDO SIMULAÇÃO GLOBAL ---")
        print("1. Injetando erro de terminal...")
        print(SimulationEngine.simulate_terminal_error())
        
        time.sleep(2)
        
        print("2. Injetando erro de log...")
        # Cria um log temporário e avisa o LogWatcher (precisa configurar o path no app real)
        print(SimulationEngine.simulate_log_error())
        
        print("--- SIMULAÇÃO CONCLUÍDA ---")

if __name__ == "__main__":
    SimulationEngine.run_full_simulation()
