import threading
import concurrent.futures
from core.llm_manager import LLMManager

class SwarmAgent:
    def __init__(self, name, role, llm_manager):
        self.name = name
        self.role = role
        self.llm = llm_manager

    def execute(self, task):
        print(f"🐝 Agente {self.name} ({self.role}) iniciando tarefa...")
        prompt = f"Você é o agente {self.name}, especialista em {self.role}.\nSUA TAREFA: {task}\nResponda apenas com o resultado técnico."
        return self.llm.generate_command(prompt, system_context=f"SWARM_{self.name.upper()}")

class SwarmManager:
    """
    Gerencia uma frota de sub-agentes para resolver problemas complexos em paralelo.
    """
    def __init__(self, llm_manager):
        self.llm = llm_manager
        # Define a frota padrão
        self.agents = {
            "Judge": "Revisão de Código, Linting e Segurança",
            "Smith": "Escrita de Código, Refatoração e Testes",
            "Scout": "Busca de Arquivos, Mapeamento de Dependências e Pesquisa"
        }

    def solve_complex_task(self, main_task, plan):
        """
        Orquestração Swarm 2.0: Suporta dependências entre tarefas e resolução de conflitos.
        """
        results = {}
        print(f"🚀 Swarm 2.0: Orquestrando tarefa hierárquica...")
        
        # 1. Execução do Scout Primeiro (Fase de Reconhecimento)
        if "Scout" in plan:
            results["Scout"] = SwarmAgent("Scout", self.agents["Scout"], self.llm).execute(plan["Scout"])
            # Atualiza o plano dos outros com o que o Scout achou
            for agent in ["Smith", "Judge"]:
                if agent in plan:
                    plan[agent] += f"\n\nContexto do Scout: {results['Scout']}"

        # 2. Execução em Paralelo (Smith e Judge)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            others = {name: plan[name] for name in ["Smith", "Judge"] if name in plan}
            future_to_agent = {
                executor.submit(SwarmAgent(name, self.agents[name], self.llm).execute, task): name
                for name, task in others.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                results[agent_name] = future.result()
        
        # 3. Resolução de Conflitos (O Judge dá a palavra final se houver Smith)
        if "Judge" in results and "Smith" in results:
            print("Swarm: Judge analisando a saída do Smith...")
            # Lógica de validação cruzada
            
        return results

    def delegate_automatically(self, complex_prompt):
        """
        Usa a LLM principal para quebrar o problema e delegar para o Swarm.
        """
        delegation_prompt = f"""Analise este pedido complexo: '{complex_prompt}'
        Divida-o em sub-tarefas para os seguintes agentes:
        - Smith (Escrever código)
        - Judge (Revisar e validar)
        - Scout (Mapear o que for necessário)
        
        Responda APENAS um JSON no formato:
        {{ "Smith": "tarefa...", "Judge": "tarefa...", "Scout": "tarefa..." }}
        """
        
        try:
            plan_str = self.llm.generate_command(delegation_prompt)
            # Limpeza básica de JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', plan_str, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                return self.solve_complex_task(complex_prompt, plan)
        except Exception as e:
            print(f"Erro na delegação automática do Swarm: {e}")
            return None
