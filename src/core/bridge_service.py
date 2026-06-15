import socket
import json
import threading
import queue
import time

class BridgeService:
    """
    Gerencia a comunicação assíncrona com o SwiftAgent.
    Evita que o Python bloqueie a UI enquanto espera resposta do hardware.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BridgeService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        self.socket_path = "/tmp/omniscient_agent.sock"
        self.request_queue = queue.Queue()
        self.results = {}
        self.running = True
        
        # Inicia o worker de processamento
        threading.Thread(target=self._bridge_worker, daemon=True).start()
        self._initialized = True

    def send_async(self, command, callback=None):
        """Envia um comando sem bloquear o chamador."""
        req_id = str(time.time())
        self.request_queue.put((req_id, command, callback))
        return req_id

    def send_sync(self, command, timeout=5):
        """Envia um comando e espera a resposta (com timeout)."""
        req_id = self.send_async(command)
        start = time.time()
        while time.time() - start < timeout:
            if req_id in self.results:
                return self.results.pop(req_id)
            time.sleep(0.05)
        return {"status": "error", "message": "Timeout na ponte Swift"}

    def _bridge_worker(self):
        while self.running:
            try:
                req_id, command, callback = self.request_queue.get(timeout=1.0)
                
                result = self._raw_send(command)
                self.results[req_id] = result
                
                if callback:
                    try:
                        callback(result)
                    except Exception as cb_err:
                        print(f"Bridge: Erro no callback: {cb_err}")
                
                self.request_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Bridge Worker Erro: {e}")

    def _raw_send(self, command_json, retry_count=3):
        for attempt in range(retry_count):
            try:
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.settimeout(10.0)
                client.connect(self.socket_path)
                client.sendall(json.dumps(command_json).encode('utf-8'))

                response = client.recv(4096)
                client.close()

                if response:
                    return json.loads(response.decode('utf-8'))
                return {"status": "success"}
            except Exception as e:
                print(f"Bridge: Tentativa {attempt+1} falhou: {e}")
                if attempt == retry_count - 1:
                    # SELF-HEALING: Tenta reiniciar o SwiftAgent se falhou tudo
                    self._restart_native_bridge()
                    return {"status": "error", "message": str(e)}
                time.sleep(1)

    def _restart_native_bridge(self):
        """Tenta reiniciar o processo nativo Swift."""
        print("Bridge: Tentando auto-healing (reiniciando SwiftAgent)...")
        try:
            # Envia comando de terminal para rodar o build do Swift se necessário
            # Ou apenas tenta matar e rodar de novo
            import subprocess
            subprocess.run(["killall", "OmniscientAgent"], capture_output=True)
            # O MainApp deve ter a lógica de garantir que ele rode, 
            # mas aqui podemos disparar um sinal.
        except:
            pass

# Instância global
bridge = BridgeService()
