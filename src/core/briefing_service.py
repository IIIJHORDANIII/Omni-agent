from datetime import datetime

class BriefingService:
    """
    Servico de briefing diario com resumo completo de produtividade,
    e-mails, calendario, tarefas e foco.
    """
    
    def __init__(self, llm_manager):
        self.llm = llm_manager

    def generate_morning_briefing(self):
        """Gera briefing matinal completo."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Bom dia"
        elif 12 <= hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"
        
        sections = []
        
        # 1. Calendario
        try:
            from core.execution_service import ExecutionService
            events = ExecutionService.get_calendar_events()
            if isinstance(events, dict):
                events_text = events.get("stdout", "").strip()
            else:
                events_text = str(events)
            if events_text and "Nenhum" not in events_text:
                sections.append(f"Eventos de hoje:\n{events_text}")
        except Exception:
            pass
        
        # 2. E-mails nao lidos
        try:
            from core.execution_service import ExecutionService
            emails = ExecutionService.mail_unread(count=5)
            if isinstance(emails, dict):
                emails_text = emails.get("stdout", "").strip()
            else:
                emails_text = str(emails)
            if emails_text and "Nenhum" not in emails_text:
                sections.append(f"E-mails importantes:\n{emails_text}")
        except Exception:
            pass
        
        # 3. Lembretes
        try:
            from core.execution_service import ExecutionService
            reminders = ExecutionService.get_reminders()
            if isinstance(reminders, dict):
                reminders_text = reminders.get("stdout", "").strip()
            else:
                reminders_text = str(reminders)
            if reminders_text and "Nenhum" not in reminders_text:
                sections.append(f"Lembretes pendentes:\n{reminders_text}")
        except Exception:
            pass
        
        # 4. Tarefas pendentes
        try:
            from core.task_manager import TaskManager
            tm = TaskManager()
            pending = tm.get_pending_tasks()
            if pending:
                task_lines = [f"  - [{t['priority']}] {t['title']}" for t in pending[:5]]
                sections.append("Tarefas prioritarias:\n" + "\n".join(task_lines))
        except Exception:
            pass
        
        # 5. Status do sistema
        try:
            from core.system_health import SystemHealth
            health = SystemHealth()
            quick = health.get_quick_status()
            sections.append(f"Sistema: {quick}")
        except Exception:
            pass
        
        # Monta briefing final
        if sections:
            briefing = f"{greeting}, Senhor. Aqui esta o resumo:\n\n"
            briefing += "\n\n".join(sections)
        else:
            briefing = f"{greeting}, Senhor. Nenhum evento importante no momento."
        
        return briefing

    def generate_evening_briefing(self, linear_info="", github_info=""):
        """Gera retrospectiva do dia."""
        sections = []
        
        # 1. Resumo de foco
        try:
            from core.deep_focus_service import DeepFocusService
            focus = DeepFocusService()
            daily = focus.get_daily_summary()
            if daily["total_sessions"] > 0:
                sections.append(
                    f"Foco do dia:\n"
                    f"  Pomodoros concluidos: {daily['completed_pomodoros']}\n"
                    f"  Tempo total focado: {daily['total_focus_minutes']} minutos"
                )
        except Exception:
            pass
        
        # 2. Tarefas concluidas
        try:
            from core.task_manager import TaskManager
            tm = TaskManager()
            today = datetime.now().date().isoformat()
            completed = [t for t in tm.tasks if t.get("completed_at", "").startswith(today)]
            if completed:
                task_lines = [f"  - {t['title']}" for t in completed[:5]]
                sections.append("Tarefas concluidas:\n" + "\n".join(task_lines))
        except Exception:
            pass
        
        # 3. Info do Linear/GitHub
        if linear_info:
            sections.append(f"Linear: {linear_info}")
        if github_info:
            sections.append(f"GitHub: {github_info}")
        
        if sections:
            briefing = "Senhor, aqui esta o resumo das suas conquistas de hoje:\n\n"
            briefing += "\n\n".join(sections)
        else:
            briefing = "Senhor, o dia foi tranquilo. Amanha podemos ser mais produtivos!"
        
        # Gera sugestao via LLM se disponivel
        if self.llm:
            try:
                prompt = f"Resumo do dia:\n{briefing}\n\n Sugira 1-2 tarefas importantes para amanha em 1 frase:"
                suggestion = self.llm.generate_command(prompt)
                briefing += f"\n\nSugestao para amanha: {suggestion}"
            except Exception:
                pass
        
        return briefing.strip()
