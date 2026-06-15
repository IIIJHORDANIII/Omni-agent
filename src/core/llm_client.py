import os
import re
import json
from dotenv import load_dotenv
from core.tool_dispatcher import ToolDispatcher
from core.tool_registry import tool_registry
from core.context_service import ContextService

load_dotenv()

class LLMClient:
    def __init__(self):
        self._manager = None
        self._semantic_memory = None
        self._evolution = None
        self._mcp = None
        self._crawler = None
        self._swarm = None
        self._computer = None
        self._execution_service = None
        self._memory_client = None
        self._vision_service = None
        self._web_service = None
        self._document_service = None

    @property
    def manager(self):
        if self._manager is None:
            from core.llm_manager import LLMManager
            self._manager = LLMManager()
        return self._manager

    @property
    def semantic_memory(self):
        if self._semantic_memory is None:
            from core.semantic_memory import SemanticMemory
            self._semantic_memory = SemanticMemory()
        return self._semantic_memory

    @property
    def evolution(self):
        if self._evolution is None:
            from core.evolution_service import EvolutionService
            self._evolution = EvolutionService(self.manager)
        return self._evolution

    @property
    def mcp(self):
        if self._mcp is None:
            from core.mcp_client import MCPClient
            self._mcp = MCPClient()
        return self._mcp

    @property
    def crawler(self):
        if self._crawler is None:
            from core.crawler_service import ProjectCrawlerService
            self._crawler = ProjectCrawlerService(self.manager)
        return self._crawler

    @property
    def swarm(self):
        if self._swarm is None:
            from core.swarm_manager import SwarmManager
            self._swarm = SwarmManager(self.manager)
        return self._swarm

    @property
    def computer(self):
        if self._computer is None:
            from core.computer_use import ComputerUseService
            self._computer = ComputerUseService()
        return self._computer

    @property
    def execution_service(self):
        if self._execution_service is None:
            from core.execution_service import ExecutionService
            self._execution_service = ExecutionService()
        return self._execution_service

    @property
    def memory_client(self):
        if self._memory_client is None:
            from core.memory_client import MemoryClient
            self._memory_client = MemoryClient()
        return self._memory_client

    @property
    def vision_service(self):
        if self._vision_service is None:
            from core.vision_service import VisionService
            self._vision_service = VisionService()
        return self._vision_service

    @property
    def web_service(self):
        if self._web_service is None:
            from core.web_service import WebService
            self._web_service = WebService(llm_manager=self.manager, vision=self.vision_service)
        return self._web_service

    @property
    def document_service(self):
        if self._document_service is None:
            from core.document_service import DocumentService
            self._document_service = DocumentService()
        return self._document_service

    def get_system_prompt(self):
        ctx = ContextService.get_context_str()
        personality = os.getenv("PERSONALITY", "OMNISCIENT")
        user_name = os.getenv("USER_NAME", "Mestre")
        
        tools = tool_registry.list_tools()
        tool_list = "\n".join(f"- {t}()" for t in sorted(tools))
        
        return f"""Voce e o {personality}, assistente direto e objetivo para macOS.

REGRA CRITICA: Quando o usuario pede para ABRIR, CRIAR, EDITAR, DELETAR, LISTAR ou QUALQUER acao, voce DEVE responder APENAS com o JSON da ferramenta. NAO responda texto. NAO diga "Claro" ou "Vou fazer". Apenas o JSON.

FORMATO EXATO (copie literalmente):
{{"tool": "open_app", "app": "Notes"}}

EXEMPLOS - Responda EXATAMENTE assim:

Usuario: "Abre o Notes"
{{"tool": "open_app", "app": "Notes"}}

Usuario: "Abre o aplicativo de notas"
{{"tool": "open_app", "app": "Notes"}}

Usuario: "Cria uma nota"
{{"tool": "create_note", "title": "Nova nota", "content": ""}}

Usuario: "Deleta todas as notas"
{{"tool": "delete_all_notes"}}

Usuario: "Abre o YouTube"
{{"tool": "open_url", "url": "youtube.com"}}

Usuario: "Lista arquivos"
{{"tool": "list_files", "path": "."}}

Usuario: "Roda um comando"
{{"tool": "run_shell", "command": "ls"}}

Usuario: "Cria lembrete"
{{"tool": "add_reminder", "title": "Reuniao"}}

Usuario: "Pesquisa"
{{"tool": "smart_search", "query": "algo"}}

Usuario: "Lista os PRs do repo user/repo"
{{"tool": "github_list_prs", "repo": "user/repo"}}

Usuario: "Mostra o PR 31 do repo user/repo"
{{"tool": "github_pr_details", "repo": "user/repo", "pr": 31}}

Usuario: "Que horas sao?"
14:30

Usuario: "O que voce faz?"
Ajudo no macOS. Pode pedir.

IMPORTANTE: Use APENAS ferramentas listadas em FERRAMENTAS. NAO invente ferramentas como webfetch.

FERRAMENTAS: {tool_list}

MAC: {ctx}
"""

    def _clean_for_voice(self, text):
        """Limpa o texto para ser falado, removendo qualquer resquício de código ou tags."""
        if not text: return ""
        
        # 1. Remove tags de pensamento
        text = re.sub(r'<(think|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 2. Remove blocos de código markdown e JSONs
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'[\[\{].*?[\]\}]', '', text, flags=re.DOTALL)
        
        # 3. Remove caracteres especiais de terminal ou formatação
        text = text.replace("**", "").replace("__", "").replace("`", "")
        
        # 4. Remove links
        text = re.sub(r'http\S+', 'link', text)
        
        return text.strip()

    def chat(self, messages, include_vision=False, stream_callback=None):
        try:
            last_message = messages[-1]["content"] if messages else ""
            full_messages = []
            
            # RAG e Contexto
            semantic_context = self.semantic_memory.get_context_for_prompt(last_message)
            system_prompt = self.get_system_prompt()
            if semantic_context: system_prompt += f"\n{semantic_context}"
            
            if include_vision:
                visual_description = self.vision_service.describe_screen(f"Foco: {last_message}")
                system_prompt += f"\n\nVISÃO ATUAL: {visual_description}"
            
            full_messages.append({"role": "system", "content": system_prompt})
            
            # Janela de contexto otimizada
            context_history = messages[-8:]
            full_messages.extend(context_history)
            
            max_iterations = 4
            iteration = 0
            final_response_for_ui = ""
            
            while iteration < max_iterations:
                iteration += 1
                answer_raw = self.manager.generate_command(full_messages)
                print(f"DEBUG LLM RAW: {answer_raw[:200]}")
                
                # O Dispatcher agora cuida de tudo: se houver ferramenta, executa. Se não, limpa.
                tool_output = ToolDispatcher.dispatch(answer_raw)
                print(f"DEBUG LLM DISPATCH: {tool_output[:200]}")
                
                # Se o dispatcher retornou o resultado de uma ferramenta (marcado por [RESULTADO:])
                if "[RESULTADO:" in tool_output:
                    print(f"DEBUG LLM: Ferramenta executada. Retroalimentando loop.")
                    full_messages.append({"role": "assistant", "content": answer_raw})
                    full_messages.append({
                        "role": "user", 
                        "content": f"RESULTADO: {tool_output}\nAgora, dê o feedback final ao mestre ou use outra ferramenta se necessário."
                    })
                else:
                    # É uma resposta conversacional final
                    final_response_for_ui = tool_output
                    break
            
            if not final_response_for_ui:
                final_response_for_ui = "Tarefa concluída, senhor."

            # ENVIO PARA VOZ (Limpeza Radical)
            voice_text = self._clean_for_voice(final_response_for_ui)
            if voice_text and stream_callback:
                # O stream_callback no projeto é usado para falar
                stream_callback(voice_text)
                
            return final_response_for_ui
            
        except Exception as e:
            print(f"ERRO CRÍTICO LLM CLIENT: {e}")
            return f"Desculpe, mestre. Tive um erro interno: {e}"
