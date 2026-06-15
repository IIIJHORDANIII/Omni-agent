import socket
import json
import threading
import queue
import time
import uuid

class BridgeService:
    """
    Gerencia a comunicação assíncrona com o SwiftAgent.
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
        self._result_events = {}
        self.running = True
        
        threading.Thread(target=self._bridge_worker, daemon=True).start()
        self._initialized = True

    def send_async(self, command, callback=None):
        req_id = uuid.uuid4().hex
        self._result_events[req_id] = threading.Event()
        self.request_queue.put((req_id, command, callback))
        return req_id

    def send_sync(self, command, timeout=5):
        req_id = self.send_async(command)
        event = self._result_events.get(req_id)
        if event and event.wait(timeout=timeout):
            return self.results.pop(req_id, {"status": "error", "message": "Resultado não encontrado"})
        return {"status": "error", "message": "Timeout na ponte Swift"}

    def _bridge_worker(self):
        while self.running:
            try:
                req_id, command, callback = self.request_queue.get(timeout=1.0)
                
                result = self._raw_send(command)
                self.results[req_id] = result
                
                event = self._result_events.pop(req_id, None)
                if event:
                    event.set()
                
                if callback:
                    try:
                        callback(result)
                    except Exception as cb_err:
                        pass
                
                self.request_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                pass

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
                if attempt == retry_count - 1:
                    self._restart_native_bridge()
                    return {"status": "error", "message": str(e)}
                time.sleep(1)

    def _restart_native_bridge(self):
        """Tenta reiniciar o processo nativo Swift."""
        try:
            import subprocess
            subprocess.run(["killall", "Omniscient"], capture_output=True)
        except Exception:
            pass

# Instância global
bridge = BridgeService()
