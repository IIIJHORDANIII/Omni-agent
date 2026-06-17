import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from core.mcp_client import MCPClient, _ensure_mcp


class TestMCPClient:
    """Testes para o MCPClient reescrito."""

    def setup_method(self):
        self.client = MCPClient()

    def test_load_config_default(self):
        """Testa se a configuracao padrao e carregada quando o arquivo nao existe."""
        assert "servers" in self.client.config
        assert "everything" in self.client.config["servers"]

    def test_add_server(self):
        """Testa adicionar um servidor a configuracao."""
        self.client.add_server("test-server", "echo", ["hello"])
        assert "test-server" in self.client.config["servers"]
        assert self.client.config["servers"]["test-server"]["command"] == "echo"

    def test_list_all_tools_empty(self):
        """Testa listagem de ferramentas quando nada esta conectado."""
        tools = self.client.list_all_tools()
        assert isinstance(tools, list)

    @patch("core.mcp_client._mcp_available", False)
    def test_connect_server_without_mcp_package(self):
        """Testa que connect_server retorna False quando mcp nao esta instalado."""
        result = self.client.connect_server("test", {"command": "echo", "args": []})
        assert result is False

    def test_call_tool_server_not_connected(self):
        """Testa chamada de ferramenta em servidor nao conectado."""
        result = self.client.call_tool("nonexistent", "tool", {})
        assert "error" in result
        assert "nao conectado" in result["error"]

    def test_call_tool_auto_not_found(self):
        """Testa chamada automatica quando ferramenta nao existe."""
        result = self.client.call_tool_auto("nonexistent_tool", {})
        assert "error" in result
        assert "nao encontrada" in result["error"]

    def test_disconnect_all_empty(self):
        """Testa desconectar quando nao ha sessoes."""
        self.client.disconnect_all()
        assert len(self.client.sessions) == 0

    def test_ensure_mcp_import(self):
        """Testa a funcao de importacao lazy do MCP."""
        # Nao deve levantar erro mesmo se mcp nao estiver instalado
        _ensure_mcp()
