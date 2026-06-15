import unittest
import os
import sys
import threading
from unittest.mock import MagicMock, patch

# Ajusta path para importar do src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from core.registry import ServiceRegistry
from core.tool_registry import ToolRegistry
from core.llm_client import LLMClient

class TestOmniscientCore(unittest.TestCase):

    def test_service_registry(self):
        """Testa se o registro de serviços funciona corretamente."""
        registry = ServiceRegistry()
        mock_service = MagicMock()
        registry.register("test_service", mock_service)
        
        self.assertEqual(registry.get("test_service"), mock_service)
        self.assertIn("test_service", registry.list_services())

    def test_tool_registry(self):
        """Testa o registro dinâmico de ferramentas."""
        tool_reg = ToolRegistry()
        
        @tool_reg.register(name="test_tool", aliases=["alias_tool"])
        def test_func(a, b):
            return a + b
            
        self.assertEqual(tool_reg.get_tool("test_tool"), test_func)
        self.assertEqual(tool_reg.get_tool("alias_tool"), test_func)
        self.assertIn("test_tool", tool_reg.list_tools())

    def test_llm_clean_response(self):
        """Testa a limpeza agressiva de pensamentos e marcadores."""
        client = LLMClient()
        
        # Teste 1: Remoção de tags think
        raw = "<think>Pequeno pensamento</think>Resposta final"
        self.assertEqual(client._clean_response(raw), "Resposta final")
        
        # Teste 2: Remoção de marcadores de texto (Multiline)
        raw2 = "Pensamento: Analisando as pastas...\nResposta limpa"
        self.assertEqual(client._clean_response(raw2), "Resposta limpa")
        
        # Teste 3: Extração de JSON (Prioridade no ReAct)
        raw3 = "Vou rodar isso agora:\n[{\"tool\": \"smart_search\", \"params\": {\"query\": \"test\"}}]"
        self.assertEqual(client._clean_response(raw3), "[{\"tool\": \"smart_search\", \"params\": {\"query\": \"test\"}}]")

    def test_react_loop_iteration(self):
        """Simula se o loop ReAct termina quando não há JSON."""
        client = LLMClient()
        client.manager.generate_command = MagicMock(return_value="Olá, mestre.")
        
        res = client.chat([{"role": "user", "content": "oi"}])
        self.assertEqual(res, "Olá, mestre.")
        self.assertTrue(client.manager.generate_command.called)

if __name__ == "__main__":
    unittest.main()
