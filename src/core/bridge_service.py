import socket
import json
import threading
import queue
import time
import os

class BridgeService:
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
        self._swift_available = None  # None = não verificado, True/False
        self._consecutive_failures = 0
        
        threading.Thread(target=self._bridge_worker, daemon=True).start()
        self._initialized = True

    def _check_swift_available(self):
        """Verifica se o SwiftAgent está rodando (uma vez só)."""
        if self._swift_available is not None:
            return self._swift_available
        self._swift_available = os.path.exists(self.socket_path)
        if not self._swift_available:
            print("Bridge: SwiftAgent não encontrado. Serviços nativos desabilitados.")
        return self._swift_available

    def send_async(self, command, callback=None):
        req_id = str(time.time())
        self.request_queue.put((req_id, command, callback))
        return req_id

    def send_sync(self, command, timeout=5):
        if not self._check_swift_available():
            return {"status": "error", "message": "SwiftAgent não disponível"}
        
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
                
                if not self._check_swift_available():
                    self.results[req_id] = {"status": "error", "message": "SwiftAgent não disponível"}
                    if callback:
                        try:
                            callback(self.results[req_id])
                        except Exception:
                            pass
                    self.request_queue.task_done()
                    continue
                
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
                    self._consecutive_failures = 0
                    return json.loads(response.decode('utf-8'))
                return {"status": "success"}
            except Exception as e:
                self._consecutive_failures += 1
                if attempt == retry_count - 1:
                    if self._consecutive_failures >= 6:
                        self._swift_available = False
                        print("Bridge: SwiftAgent indisponível. Parando tentativas.")
                    return {"status": "error", "message": str(e)}
                time.sleep(1)

bridge = BridgeService()
