from core.context_service import ContextService
from core.system_monitor import SystemMonitor

class BriefingService:
    def __init__(self, llm_manager):
        self.llm = llm_manager

    def generate_morning_briefing(self):
        """Gera apenas uma saudação inicial baseada na hora."""
        from datetime import datetime
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Bom dia"
        elif 12 <= hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"

        return f"{greeting}, Senhor."


    def generate_evening_briefing(self, linear_info, github_info):
        """Gera uma retrospectiva do dia."""
        prompt = f"""Você é o JARVIS. O dia de trabalho está terminando.
Sua tarefa é cruzar as informações de progresso e gerar uma retrospectiva elegante.

DADOS DO LINEAR:
{linear_info}

DADOS DO GITHUB:
{github_info}

REGRAS:
1. Comece com "Senhor, aqui está o resumo das suas conquistas de hoje."
2. Liste os destaques (issues concluídas e PRs).
3. Se não houve progresso claro, seja diplomático e sugira foco para amanhã.
4. Termine com uma sugestão de pauta para amanhã baseada no que foi visto.
5. Tom formal, estilo mordomo britânico altamente inteligente.
"""
        response = self.llm.generate_command(prompt, system_context="RETROSPECTIVA_DIARIA")
        return response.strip()
