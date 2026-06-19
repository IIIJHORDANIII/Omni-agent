import os
import json
import time
import threading
from datetime import datetime, timedelta

class TaskManager:
    """
    Gerenciador de tarefas inteligente com LLM, persistencia em JSON,
    e integracao com calendario/lembretes.
    """
    
    PRIORITY_HIGH = "alta"
    PRIORITY_MEDIUM = "media"
    PRIORITY_LOW = "baixa"
    
    STATUS_PENDING = "pendente"
    STATUS_IN_PROGRESS = "em_andamento"
    STATUS_COMPLETED = "concluida"
    STATUS_CANCELLED = "cancelada"
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.tasks = []
        self._tasks_file = os.path.expanduser("~/.config/anders/tasks.json")
        self._lock = threading.Lock()
        self._load_tasks()

    def _load_tasks(self):
        """Carrega tarefas do arquivo JSON."""
        try:
            if os.path.exists(self._tasks_file):
                with open(self._tasks_file, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
        except Exception:
            self.tasks = []

    def _save_tasks(self):
        """Salva tarefas no arquivo JSON."""
        try:
            os.makedirs(os.path.dirname(self._tasks_file), exist_ok=True)
            with open(self._tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"TaskManager: Erro ao salvar: {e}")

    def add_task(self, title, description="", priority=None, due_date=None, tags=None):
        """Adiciona uma nova tarefa."""
        with self._lock:
            task = {
                "id": int(time.time() * 1000),
                "title": title,
                "description": description,
                "priority": priority or self.PRIORITY_MEDIUM,
                "status": self.STATUS_PENDING,
                "created_at": datetime.now().isoformat(),
                "due_date": due_date,
                "tags": tags or [],
                "subtasks": [],
                "notes": ""
            }
            self.tasks.append(task)
            self._save_tasks()
            return task

    def add_task_from_natural(self, text):
        """Cria tarefa a partir de texto natural usando LLM."""
        if not self.llm:
            return self.add_task(text)
        
        prompt = f"""
        Extraia uma tarefa desta mensagem: "{text}"
        Retorne APENAS um JSON com: {{"title": "...", "priority": "alta/media/baixa", "due_date": "YYYY-MM-DD ou null", "tags": ["tag1"]}}
        """
        
        try:
            response = self.llm.manager.generate_command(prompt)
            # Tenta extrair JSON da resposta
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return self.add_task(
                    title=data.get("title", text),
                    priority=data.get("priority"),
                    due_date=data.get("due_date"),
                    tags=data.get("tags", [])
                )
        except Exception:
            pass
        
        return self.add_task(text)

    def complete_task(self, task_id):
        """Marca uma tarefa como concluida."""
        with self._lock:
            for task in self.tasks:
                if task["id"] == task_id:
                    task["status"] = self.STATUS_COMPLETED
                    task["completed_at"] = datetime.now().isoformat()
                    self._save_tasks()
                    return task
            return None

    def delete_task(self, task_id):
        """Remove uma tarefa."""
        with self._lock:
            self.tasks = [t for t in self.tasks if t["id"] != task_id]
            self._save_tasks()

    def update_task(self, task_id, **kwargs):
        """Atualiza campos de uma tarefa."""
        with self._lock:
            for task in self.tasks:
                if task["id"] == task_id:
                    for key, value in kwargs.items():
                        if key in task:
                            task[key] = value
                    task["updated_at"] = datetime.now().isoformat()
                    self._save_tasks()
                    return task
            return None

    def get_tasks(self, status=None, priority=None, tags=None):
        """Retorna tarefas filtradas."""
        filtered = self.tasks
        
        if status:
            filtered = [t for t in filtered if t["status"] == status]
        if priority:
            filtered = [t for t in filtered if t["priority"] == priority]
        if tags:
            filtered = [t for t in filtered if any(tag in t.get("tags", []) for tag in tags)]
        
        return filtered

    def get_pending_tasks(self):
        """Retorna tarefas pendentes ordenadas por prioridade."""
        priority_order = {self.PRIORITY_HIGH: 0, self.PRIORITY_MEDIUM: 1, self.PRIORITY_LOW: 2}
        pending = self.get_tasks(status=self.STATUS_PENDING)
        return sorted(pending, key=lambda t: priority_order.get(t["priority"], 1))

    def get_overdue_tasks(self):
        """Retorna tarefas atrasadas."""
        now = datetime.now().date()
        overdue = []
        for task in self.tasks:
            if task["status"] == self.STATUS_PENDING and task.get("due_date"):
                try:
                    due = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
                    if due < now:
                        overdue.append(task)
                except ValueError:
                    pass
        return overdue

    def get_today_tasks(self):
        """Retorna tarefas de hoje."""
        today = datetime.now().date().isoformat()
        return [t for t in self.tasks if t.get("due_date") == today]

    def add_subtask(self, task_id, subtask_title):
        """Adiciona subtask a uma tarefa."""
        with self._lock:
            for task in self.tasks:
                if task["id"] == task_id:
                    subtask = {
                        "id": int(time.time() * 1000),
                        "title": subtask_title,
                        "completed": False
                    }
                    task.setdefault("subtasks", []).append(subtask)
                    self._save_tasks()
                    return subtask
            return None

    def complete_subtask(self, task_id, subtask_id):
        """Marca subtask como concluida."""
        with self._lock:
            for task in self.tasks:
                if task["id"] == task_id:
                    for sub in task.get("subtasks", []):
                        if sub["id"] == subtask_id:
                            sub["completed"] = True
                            self._save_tasks()
                            return sub
            return None

    def get_summary(self):
        """Retorna resumo das tarefas."""
        pending = self.get_tasks(status=self.STATUS_PENDING)
        in_progress = self.get_tasks(status=self.STATUS_IN_PROGRESS)
        completed = self.get_tasks(status=self.STATUS_COMPLETED)
        overdue = self.get_overdue_tasks()
        
        return {
            "total": len(self.tasks),
            "pendentes": len(pending),
            "em_andamento": len(in_progress),
            "concluidas": len(completed),
            "atrasadas": len(overdue),
            "por_prioridade": {
                "alta": len([t for t in pending if t["priority"] == self.PRIORITY_HIGH]),
                "media": len([t for t in pending if t["priority"] == self.PRIORITY_MEDIUM]),
                "baixa": len([t for t in pending if t["priority"] == self.PRIORITY_LOW]),
            }
        }

    def suggest_next_task(self):
        """Usa LLM para sugerir a proxima tarefa."""
        pending = self.get_pending_tasks()
        if not pending:
            return "Nenhuma tarefa pendente!"
        
        overdue = self.get_overdue_tasks()
        if overdue:
            return f"Atencao: {len(overdue)} tarefa(s) atrasada(s)! Priorize: {overdue[0]['title']}"
        
        if self.llm:
            tasks_text = "\n".join([
                f"- [{t['priority']}] {t['title']} (due: {t.get('due_date', 'sem prazo')})"
                for t in pending[:5]
            ])
            prompt = f"Tarefas pendentes:\n{tasks_text}\n\nQual a proxima tarefa mais importante e por que? Responda em 1 frase."
            try:
                suggestion = self.llm.manager.generate_command(prompt)
                return suggestion
            except Exception:
                pass
        
        # Fallback: retorna a primeira de maior prioridade
        return f"Priorize: {pending[0]['title']}"

    def format_for_display(self, tasks=None):
        """Formata tarefas para exibicao."""
        if tasks is None:
            tasks = self.get_pending_tasks()
        
        if not tasks:
            return "Nenhuma tarefa pendente."
        
        lines = []
        priority_icons = {"alta": "!!!", "media": "!!", "baixa": "!"}
        
        for task in tasks[:10]:
            icon = priority_icons.get(task["priority"], "-")
            due = task.get("due_date", "")
            due_str = f" (due: {due})" if due else ""
            lines.append(f"[{icon}] {task['title']}{due_str}")
        
        return "\n".join(lines)
