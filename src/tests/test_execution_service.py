import pytest
from unittest.mock import patch, MagicMock
from core.execution_service import ExecutionService

def test_run_terminal_command_success():
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "hello world"
        mock_res.stderr = ""
        mock_run.return_value = mock_res
        
        result = ExecutionService.run_terminal_command("echo hello")
        assert result["stdout"] == "hello world"
        assert result["exit_code"] == 0

def test_open_app_url_redirect():
    with patch("core.execution_service.ExecutionService.open_url") as mock_open_url:
        ExecutionService.open_app("https://google.com")
        mock_open_url.assert_called_once_with("https://google.com")

def test_resolve_path_found():
    with patch("core.execution_service.ExecutionService.run_terminal_command") as mock_cmd:
        mock_cmd.return_value = {"stdout": "/Users/test/Documents/pessoal/payjota", "returncode": 0}
        
        path = ExecutionService.resolve_path("payjota")
        assert path == "/Users/test/Documents/pessoal/payjota"
