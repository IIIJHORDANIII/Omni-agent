import asyncio
import os
import json
import threading

# Importacao lazy do MCP para evitar erro se nao estiver instalado
_mcp_available = False
ClientSession = None
StdioServerParameters = None

def _ensure_mcp():
    global _mcp_available, ClientSession, StdioServerParameters
    if not _mcp_available:
        try:
            from mcp import ClientSession as _CS, StdioServerParameters as _SP
            ClientSession = _CS
            StdioServerParameters = _SP
            _mcp_available = True
        except ImportError:
            print("MCP: Pacote 'mcp' nao instalado. Execute: pip install mcp")
            _mcp_available = False


class MCPClient:
    """
    Cliente MCP 2.0 (Universal Connectivity).
    Suporta multiplos servidores com sessoes persistentes e descoberta dinamica.
    """
    def __init__(self):
        self.sessions = {}  # server_name -> {"session": ClientSession, "read": stream, "write": stream}
        self.config_path = "memory_db/mcp_config.json"
        self._tools_cache = {}  # server_name -> list of tools
        self._loop = None
        self._thread = None
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "servers": {
                    "everything": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-everything"]
                    }
                }
            }

    def _get_loop(self):
        """Retorna ou cria o event loop em thread dedicada."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()
        return self._loop

    def _run_async(self, coro):
        """Executa uma coroutine no loop de eventos dedicado."""
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=30)

    def connect_all(self):
        """Conecta a todos os servidores configurados (sincrono)."""
        _ensure_mcp()
        if not _mcp_available:
            print("MCP: Pacote nao disponivel. Modo limitado.")
            return
        for name, params in self.config["servers"].items():
            self.connect_server(name, params)

    def connect_server(self, name, params):
        """Conecta a um servidor MCP individual."""
        _ensure_mcp()
        if not _mcp_available:
            print(f"MCP: Nao foi possivel conectar '{name}' - pacote indisponivel.")
            return False

        if name in self.sessions:
            print(f"MCP: Servidor '{name}' ja conectado.")
            return True

        try:
            server_params = StdioServerParameters(
                command=params["command"],
                args=params.get("args", []),
                env=params.get("env", os.environ.copy())
            )
            print(f"MCP: Conectando ao servidor '{name}'...")
            self._run_async(self._connect_and_store(name, server_params))
            print(f"MCP: Servidor '{name}' conectado com sucesso.")
            return True
        except Exception as e:
            print(f"MCP: Falha ao conectar em '{name}': {e}")
            return False

    async def _connect_and_store(self, name, server_params):
        """Conecta e armazena a sessao persistente."""
        from mcp.client.stdio import stdio_client
        # stdio_client retorna (read_stream, write_stream)
        read_stream, write_stream = await stdio_client(server_params).__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()

        # Descobre ferramentas disponiveis
        tools_result = await session.list_tools()
        self._tools_cache[name] = [
            {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
            for t in tools_result.tools
        ]

        self.sessions[name] = {
            "session": session,
            "read": read_stream,
            "write": write_stream
        }

    def list_all_tools(self):
        """Lista todas as ferramentas de todos os servidores conectados."""
        if not self._tools_cache:
            self.connect_all()
        all_tools = []
        for server_name, tools in self._tools_cache.items():
            for tool in tools:
                all_tools.append({
                    "server": server_name,
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool.get("inputSchema", {})
                })
        return all_tools

    def call_tool(self, server_name, tool_name, arguments):
        """Chama uma ferramenta em um servidor especifico."""
        if server_name not in self.sessions:
            return {"error": f"Servidor '{server_name}' nao conectado. Chame connect_server primeiro."}

        try:
            result = self._run_async(
                self.sessions[server_name]["session"].call_tool(tool_name, arguments)
            )
            return {"result": result}
        except Exception as e:
            return {"error": f"Erro ao chamar {tool_name}: {e}"}

    def call_tool_auto(self, tool_name, arguments):
        """Busca a ferramenta em todos os servidores e chama automaticamente."""
        for server_name, tools in self._tools_cache.items():
            for tool in tools:
                if tool["name"] == tool_name:
                    return self.call_tool(server_name, tool_name, arguments)
        return {"error": f"Ferramenta '{tool_name}' nao encontrada em nenhum servidor MCP."}

    def disconnect_all(self):
        """Desconecta de todos os servidores."""
        for name in list(self.sessions.keys()):
            try:
                session_data = self.sessions.pop(name)
                self._run_async(session_data["session"].__aexit__(None, None, None))
                print(f"MCP: Servidor '{name}' desconectado.")
            except Exception as e:
                print(f"MCP: Erro ao desconectar '{name}': {e}")
        self._tools_cache.clear()

    def add_server(self, name, command, args=None):
        """Adiciona um servidor a configuracao e salva."""
        self.config["servers"][name] = {
            "command": command,
            "args": args or []
        }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
        print(f"MCP: Servidor '{name}' adicionado a configuracao.")
