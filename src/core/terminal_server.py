import socket
import threading
import json

class TerminalOverwatchServer:
    """
    Servidor UDP leve que escuta sinais de erro vindos do terminal (zsh/bash).
    """
    def __init__(self, host='127.0.0.1', port=9999, callback=None):
        self.host = host
        self.port = port
        self.callback = callback
        self.running = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.running = True
            threading.Thread(target=self._listen_loop, daemon=True).start()
            print(f"Terminal Overwatch: Escutando em {self.host}:{self.port}")
        except Exception as e:
            print(f"Erro ao iniciar servidor Terminal Overwatch: {e}")

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = data.decode('utf-8')
                print(f"Terminal Overwatch: Sinal recebido: {message}")
                
                if self.callback:
                    # Formato esperado: "cmd|exit_code|last_output"
                    parts = message.split('|', 2)
                    if len(parts) >= 2:
                        payload = {
                            "command": parts[0],
                            "exit_code": parts[1],
                            "output": parts[2] if len(parts) > 2 else ""
                        }
                        self.callback(payload)
            except Exception as e:
                print(f"Erro no loop do Terminal Overwatch: {e}")

    def stop(self):
        self.running = False
        self.socket.close()

# Snippet para o .zshrc do usuário:
# function precmd() {
#   local exit_status=$?
#   if [ $exit_status -ne 0 ]; then
#     local last_cmd=$(fc -ln -1)
#     echo -n "$last_cmd|$exit_status" | nc -u -w0 127.0.0.1 9999
#   fi
# }
