import pytest
from unittest.mock import patch, MagicMock
from core.llm_client import LLMClient

@pytest.fixture
def llm_client():
    with patch("core.semantic_memory.SemanticMemory") as mock_sem:
        with patch("core.evolution_service.EvolutionService") as mock_evo:
            with patch("core.mcp_client.MCPClient") as mock_mcp:
                # Mock instances
                mock_sem.return_value = MagicMock()
                mock_evo.return_value = MagicMock()
                mock_mcp.return_value = MagicMock()
                
                client = LLMClient()
                client.manager = MagicMock()
                return client

def test_chat_simple_response(llm_client):
    llm_client.manager.generate_streaming.return_value = ["Olá, ", "Senhor!"]
    
    stream_results = []
    def callback(s): stream_results.append(s)
    
    response = llm_client.chat([{"role": "user", "content": "Oi"}], stream_callback=callback)
    
    assert "Olá, Senhor!" in response
    assert len(stream_results) == 2
    llm_client.manager.generate_streaming.assert_called_once()

def test_chat_tool_execution(llm_client):
    # Mock first pass to return a tool JSON, then synthesis pass
    llm_client.manager.generate_command.side_effect = [
        '[{"tool": "open_app", "params": {"app": "Notes"}}]',
        "Nota aberta!"
    ]
    
    with patch("core.tool_dispatcher.ToolDispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = "Resultado do Notas"
        
        response = llm_client.chat([{"role": "user", "content": "Abre nota"}])
        
        assert response == "Nota aberta!"
        mock_dispatch.assert_called_once()
