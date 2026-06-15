import os
import time
from core.llm_manager import LLMManager

class EvolutionService:
    """
    Loop de Auto-Evolução inspirado no Hermes Agent.
    Monitora tarefas complexas concluídas e gera novas SKILLS automaticamente.
    """
    def __init__(self, llm_manager=None):
        self.llm = llm_manager or LLMManager()
        self.skills_dir = os.path.expanduser("~/Documents/pessoal/agent/src/skills")
        os.makedirs(self.skills_dir, exist_ok=True)
        
    def evaluate_and_evolve(self, task_description, steps_taken, final_result):
        """
        Avalia se a tarefa recém-concluída foi complexa o suficiente para virar uma Skill.
        Se sim, gera e salva o SKILL.md.
        """
        print("🧠 Evolution Service: Avaliando tarefa para extração de habilidade...")
        
        prompt = f"""Você é o arquiteto de evolução do OMNISCIENT.
Uma tarefa foi concluída com sucesso. Avalie se ela representa um padrão ou fluxo de trabalho complexo que deve ser salvo como uma Habilidade (Skill) permanente para o futuro.

TAREFA ORIGINAL: {task_description}
PASSOS EXECUTADOS: {steps_taken}
RESULTADO FINAL: {final_result}

Se a tarefa for trivial (ex: abrir um app, pesquisar preço), responda apenas 'SKIP'.
Se for um fluxo valioso (ex: deploy, refatoração estrutural, setup de banco, resolução de bug complexo), crie um arquivo SKILL.md formatado.

FORMATO OBRIGATÓRIO (se for criar):
# Habilidade: [Nome da Habilidade]
Use esta habilidade quando...
## Processo Obrigatório
1. Passo 1
2. Passo 2
## Tabela Anti-Racionalização
| Desculpa | Resposta |
## Verificação Final
- Check 1
"""
        try:
            response = self.llm.generate_command(prompt, system_context="EVOLUTION_FORGE")

            if "SKIP" in response.upper() and len(response) < 20:
                print("Evolution Service: Tarefa trivial. Nenhuma skill nova gerada.")
                return False

            # Validacao do conteudo gerado
            validation = self._validate_skill(response)
            if not validation["valid"]:
                print(f"Evolution Service: Skill rejeitada - {validation['reason']}")
                return False

            # Extrai o titulo para nomear a pasta
            first_line = response.split('\n')[0]
            skill_name = first_line.replace("# Habilidade:", "").strip().lower().replace(" ", "_").replace("/", "-")
            if not skill_name or len(skill_name) < 3:
                skill_name = f"auto_skill_{int(time.time())}"

            # Verifica duplicatas
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.exists(skill_path):
                print(f"Evolution Service: Skill '{skill_name}' ja existe. Pulando.")
                return False

            os.makedirs(skill_path, exist_ok=True)

            with open(os.path.join(skill_path, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(response)

            print(f"EVOLUCAO: Nova habilidade '{skill_name}' aprendida e salva!")
            return skill_name

        except Exception as e:
            print(f"Erro no Evolution Service: {e}")
            return False

    def _validate_skill(self, skill_content):
        """Valida se o conteudo da skill e util e seguro."""
        if not skill_content or len(skill_content) < 50:
            return {"valid": False, "reason": "Conteudo muito curto"}

        required_sections = ["# Habilidade", "## Processo", "## Verificacao"]
        for section in required_sections:
            if section.lower() not in skill_content.lower():
                # Tenta formatos alternativos
                alt_sections = ["# Habilidade", "# Skill", "## Passos", "## Steps"]
                if not any(s.lower() in skill_content.lower() for s in alt_sections):
                    return {"valid": False, "reason": f"Secao obrigatoria '{section}' ausente"}

        # Verifica se nao contem comandos perigosos
        dangerous = ["rm -rf", "sudo rm", "chmod 777", "eval(", "exec("]
        for d in dangerous:
            if d in skill_content:
                return {"valid": False, "reason": f"Conteudo contem comando perigoso: {d}"}

        # Verifica se nao e apenas repeticoes
        lines = [l.strip() for l in skill_content.split('\n') if l.strip()]
        if len(set(lines)) < len(lines) * 0.5:
            return {"valid": False, "reason": "Conteudo excessivamente repetitivo"}

        return {"valid": True, "reason": "OK"}
