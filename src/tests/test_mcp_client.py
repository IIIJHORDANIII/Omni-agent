import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.mcp_client import MCPClient

@pytest.mark.asyncio
async def test_mcp_connect_success():
    with patch("core.mcp_client.stdio_client") as mock_stdio:
        # Mocking the async context managers
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        with patch("core.mcp_client.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            client = MCPClient()
            success = await client.connect()
            
            assert success is True
            mock_session.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_mcp_call_tool():
    client = MCPClient()
    client.session = AsyncMock()
    client.session.call_tool.return_value = "Tool Result"
    
    result = await client.call_tool("echo", {"msg": "hello"})
    
    assert result == "Tool Result"
    client.session.call_tool.assert_called_once_with("echo", {"msg": "hello"})
