from core.tool_registry import tool_registry
import os

@tool_registry.register(name="start_focus", aliases=["iniciar_foco", "pomodoro"])
def start_focus(duration=None, task=None, tarefa=None):
    """Inicia uma sessao de foco Pomodoro."""
    from core.deep_focus_service import DeepFocusService
    from main import MainApp
    main_app = MainApp.instance()
    focus = DeepFocusService(
        voice_service=main_app.chat_window.voice_service if main_app else None,
        hud=main_app.hud if main_app else None
    )
    return focus.start_focus(duration_min=duration, task_name=task or tarefa or "")

@tool_registry.register(name="stop_focus", aliases=["parar_foco"])
def stop_focus():
    """Para a sessao de foco atual."""
    from core.deep_focus_service import DeepFocusService
    focus = DeepFocusService()
    return focus.stop_focus()

@tool_registry.register(name="focus_status", aliases=["status_foco"])
def focus_status():
    """Retorna o status do modo foco."""
    from core.deep_focus_service import DeepFocusService
    focus = DeepFocusService()
    status = focus.get_status()
    if status["state"] == "idle":
        return f"Foco inativo. Pomodoros hoje: {status['pomodoros_hoje']}"
    return f"Foco ativo: {status['remaining_formatted']} restante (Pomodoro #{status['pomodoro_number']})"

@tool_registry.register(name="add_task", aliases=["criar_tarefa", "nova_tarefa"])
def add_task(title=None, description=None, priority=None, due=None, tags=None):
    """Adiciona uma nova tarefa."""
    from core.task_manager import TaskManager
    tm = TaskManager()
    if not title:
        return "Forneca um titulo para a tarefa."
    task = tm.add_task(title, description or "", priority=priority, due_date=due, tags=tags or [])
    return f"Tarefa criada: {task['title']} (ID: {task['id']})"

@tool_registry.register(name="add_task_natural", aliases=["criar_tarefa_natural"])
def add_task_natural(text=None):
    """Cria tarefa a partir de texto natural."""
    if not text:
        return "Descreva a tarefa."
    from core.task_manager import TaskManager
    from main import MainApp
    main_app = MainApp.instance()
    llm = main_app.chat_window.llm_client if main_app else None
    tm = TaskManager(llm_client=llm)
    task = tm.add_task_from_natural(text)
    return f"Tarefa criada: {task['title']}"

@tool_registry.register(name="complete_task", aliases=["concluir_tarefa"])
def complete_task(id=None, task_id=None):
    """Marca uma tarefa como concluida."""
    from core.task_manager import TaskManager
    tm = TaskManager()
    tid = id or task_id
    if not tid:
        return "Forneca o ID da tarefa."
    result = tm.complete_task(int(tid))
    if result:
        return f"Tarefa concluida: {result['title']}"
    return "Tarefa nao encontrada."

@tool_registry.register(name="list_tasks", aliases=["listar_tarefas", "ver_tarefas"])
def list_tasks(status=None, priority=None):
    """Lista tarefas pendentes."""
    from core.task_manager import TaskManager
    tm = TaskManager()
    if status or priority:
        tasks = tm.get_tasks(status=status, priority=priority)
    else:
        tasks = tm.get_pending_tasks()
    if not tasks:
        return "Nenhuma tarefa encontrada."
    return tm.format_for_display(tasks)

@tool_registry.register(name="task_summary", aliases=["resumo_tarefas"])
def task_summary():
    """Retorna resumo das tarefas."""
    from core.task_manager import TaskManager
    tm = TaskManager()
    summary = tm.get_summary()
    return (
        f"Total: {summary['total']} | "
        f"Pendentes: {summary['pendentes']} | "
        f"Em andamento: {summary['em_andamento']} | "
        f"Atrasadas: {summary['atrasadas']}"
    )

@tool_registry.register(name="suggest_task", aliases=["sugerir_tarefa"])
def suggest_task():
    """Sugere a proxima tarefa mais importante."""
    from core.task_manager import TaskManager
    from main import MainApp
    main_app = MainApp.instance()
    llm = main_app.chat_window.llm_client if main_app else None
    tm = TaskManager(llm_client=llm)
    return tm.suggest_next_task()

@tool_registry.register(name="system_health", aliases=["saude_sistema", "health_check"])
def system_health():
    """Verifica saude completa do sistema."""
    from core.system_health import SystemHealth
    health = SystemHealth()
    report = health.check_all()
    
    lines = [f"Status geral: {report['overall_status'].upper()}"]
    for name, check in report.items():
        if name in ("overall_status", "issues"):
            continue
        if isinstance(check, dict) and "message" in check:
            lines.append(f"  {name}: {check['message']}")
    
    if report.get("issues"):
        lines.append("\nProblemas:")
        for issue in report["issues"]:
            lines.append(f"  - {issue}")
    
    return "\n".join(lines)

@tool_registry.register(name="battery_status", aliases=["status_bateria"])
def battery_status():
    """Retorna status da bateria."""
    from core.battery_guard import BatteryGuard
    guard = BatteryGuard()
    status = guard.get_status()
    
    if not status.get("available"):
        return status.get("message", "Bateria indisponivel")
    
    percent = status["percent"]
    plugged = status["power_plugged"]
    remaining = status.get("remaining", "")
    
    msg = f"Bateria: {percent}%"
    if plugged:
        msg += " (carregando)"
    elif remaining:
        msg += f" - {remaining} restantes"
    
    return msg

@tool_registry.register(name="get_top_processes", aliases=["processos_top"])
def get_top_processes(count=5):
    """Retorna processos que mais consomem recursos."""
    from core.system_health import SystemHealth
    health = SystemHealth()
    procs = health.get_top_processes(count)
    
    lines = ["Top processos por CPU:"]
    for p in procs["top_cpu"]:
        lines.append(f"  {p['name']} (PID {p['pid']}): {p['cpu']}%")
    
    lines.append("\nTop processos por Memoria:")
    for p in procs["top_memory"]:
        lines.append(f"  {p['name']} (PID {p['pid']}): {p['mem']}%")
    
    return "\n".join(lines)

@tool_registry.register(name="daily_briefing", aliases=["briefing_diario"])
def daily_briefing():
    """Gera briefing matinal completo."""
    from core.briefing_service import BriefingService
    from core.llm_manager import LLMManager
    llm = LLMManager()
    briefing = BriefingService(llm)
    return briefing.generate_morning_briefing()

@tool_registry.register(name="evening_briefing", aliases=["briefing_noturno"])
def evening_briefing():
    """Gera retrospectiva do dia."""
    from core.briefing_service import BriefingService
    from core.llm_manager import LLMManager
    llm = LLMManager()
    briefing = BriefingService(llm)
    return briefing.generate_evening_briefing()

@tool_registry.register(name="organize_downloads", aliases=["organizar_downloads"])
def organize_downloads():
    """Organiza arquivos existentes na pasta Downloads."""
    from core.auto_organizer import AutoOrganizerService
    org = AutoOrganizerService()
    return org.organize_all()

@tool_registry.register(name="scan_duplicates", aliases=["buscar_duplicados"])
def scan_duplicates():
    """Encontra arquivos duplicados na pasta organizada."""
    from core.auto_organizer import AdvancedOrganizer
    org = AdvancedOrganizer()
    dupes = org.scan_duplicates()
    if not dupes:
        return "Nenhum arquivo duplicado encontrado."
    lines = [f"{len(dupes)} duplicados encontrados:"]
    for d in dupes[:5]:
        lines.append(f"  {os.path.basename(d['duplicate'])} ({d['size_mb']}MB) duplica {os.path.basename(d['original'])}")
    return "\n".join(lines)

@tool_registry.register(name="cleanup_old_files", aliases=["limpar_antigos"])
def cleanup_old_files(days=30):
    """Remove arquivos antigos (padrao: 30 dias)."""
    from core.auto_organizer import AdvancedOrganizer
    org = AdvancedOrganizer()
    old = org.cleanup_old_files(days=days, dry_run=True)
    if not old:
        return "Nenhum arquivo antigo encontrado."
    total_size = sum(f["size_mb"] for f in old)
    return f"{len(old)} arquivos antigos encontrados ({total_size:.1f}MB total). Dica: use 'limpar definitivamente' para remover."

@tool_registry.register(name="organizer_stats", aliases=["stats_organizador"])
def organizer_stats():
    """Retorna estatisticas da organizacao."""
    from core.auto_organizer import AdvancedOrganizer
    org = AdvancedOrganizer()
    stats = org.get_stats()
    if not stats.get("organized"):
        return "Pasta _Organizado ainda nao existe. Use 'organizar_downloads' primeiro."
    lines = [
        f"Total: {stats['total_files']} arquivos ({stats['total_size_mb']}MB)",
        "Por pasta:"
    ]
    for folder, count in sorted(stats["by_folder"].items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  {folder}: {count}")
    return "\n".join(lines)

@tool_registry.register(name="search_files", aliases=["buscar_arquivos"])
def search_files(query=None):
    """Busca arquivos por nome na pasta organizada."""
    if not query:
        return "Forneça um termo de busca."
    from core.auto_organizer import AdvancedOrganizer
    org = AdvancedOrganizer()
    results = org.search_files(query)
    if not results:
        return f"Nenhum arquivo encontrado para '{query}'."
    lines = [f"{len(results)} resultados para '{query}':"]
    for r in results[:5]:
        lines.append(f"  {r['name']} ({r['size_mb']}MB)")
    return "\n".join(lines)
