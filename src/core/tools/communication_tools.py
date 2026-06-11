from core.tool_registry import tool_registry
from core.execution_service import ExecutionService

@tool_registry.register(name="mail_unread", aliases=["unread_emails"])
def mail_unread(count=10):
    return ExecutionService.mail_unread(count)

@tool_registry.register(name="mail_list")
def mail_list(count=5):
    return ExecutionService.get_latest_emails(count)

@tool_registry.register(name="mail_draft")
def mail_draft(subject="Sem Assunto", body="", recipient=""):
    return ExecutionService.mail_create_draft(subject, body, recipient)

@tool_registry.register(name="mail_search")
def mail_search(query=""):
    return ExecutionService.mail_search(query)

@tool_registry.register(name="add_reminder")
def add_reminder(title=None, name=None):
    target = title or name or ""
    return ExecutionService.add_reminder(target)

@tool_registry.register(name="get_calendar_events")
def get_calendar_events():
    return ExecutionService.get_calendar_events()

@tool_registry.register(name="get_reminders")
def get_reminders():
    return ExecutionService.get_reminders()
