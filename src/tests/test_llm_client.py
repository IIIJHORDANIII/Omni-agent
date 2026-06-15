import pytest
from unittest.mock import patch, MagicMock
from core.llm_client import LLMClient


@pytest.fixture
def llm_client():
    with patch("core.semantic_memory.SemanticMemory") as mock_sem:
        with patch("core.evolution_service.EvolutionService") as mock_evo:
            with patch("core.mcp_client.MCPClient") as mock_mcp:
                mock_sem_inst = MagicMock()
                mock_sem_inst.get_context_for_prompt.return_value = ""
                mock_sem.return_value = mock_sem_inst
                mock_evo.return_value = MagicMock()
                mock_mcp.return_value = MagicMock()

                client = LLMClient()
                client._manager = MagicMock()
                client._semantic_memory = mock_sem_inst
                return client


def test_chat_simple_response(llm_client):
    llm_client._manager.generate_command.return_value = "Ola, Jhordan!"

    with patch("core.tool_dispatcher.ToolDispatcher.dispatch") as mock_dispatch:
        mock_dispatch.return_value = "Ola, Jhordan!"

        response = llm_client.chat([{"role": "user", "content": "Oi"}])

        assert "Ola, Jhordan!" in response
        llm_client._manager.generate_command.assert_called_once()


def test_chat_tool_execution(llm_client):
    llm_client._manager.generate_command.side_effect = [
        '[{"tool": "open_app", "params": {"app": "Notes"}}]',
        "Nota aberta!"
    ]

    with patch("core.tool_dispatcher.ToolDispatcher.dispatch") as mock_dispatch:
        mock_dispatch.side_effect = [
            "[RESULTADO: open_app] SUCCESS\nApp Notes aberto",
            "Nota aberta!"
        ]

        response = llm_client.chat([{"role": "user", "content": "Abre nota"}])

        assert "Nota aberta!" in response
        assert mock_dispatch.call_count == 2
