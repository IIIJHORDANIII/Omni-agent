import pytest
import json
from unittest.mock import patch, MagicMock
from core.tool_dispatcher import ToolDispatcher

def test_dispatch_simple_tool():
    llm_response = json.dumps([{"tool": "open_app", "params": {"app": "Notes"}}])
    
    with patch("core.execution_service.ExecutionService.open_app") as mock_open:
        mock_open.return_value = {"stdout": "App opened", "returncode": 0}
        
        # We need to mock MainApp.instance() since dispatch uses it for HUD
        with patch("main.MainApp.instance") as mock_app_instance:
            mock_app_instance.return_value = MagicMock()
            
            result = ToolDispatcher.dispatch(llm_response)
            assert "App opened" in result
            mock_open.assert_called_once()

def test_dispatch_invalid_json():
    result = ToolDispatcher.dispatch("This is not JSON")
    assert result == "This is not JSON"
