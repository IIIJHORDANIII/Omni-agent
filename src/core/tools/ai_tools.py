from core.tool_registry import tool_registry

@tool_registry.register(name="analyze_screen", aliases=["describe_screen"])
def analyze_screen():
    from core.vision_service import VisionService
    return VisionService().describe_screen()

@tool_registry.register(name="vision_action")
def vision_action(action=None, x=None, y=None, text=None):
    from main import MainApp
    app = MainApp.instance()
    if not app or not hasattr(app, 'chat_window'):
        return "Erro: Aplicativo não inicializado."
    computer = getattr(app.chat_window.llm_client, 'computer', None)
    if not computer:
        return "Erro: Computer vision não disponível."
    return computer.vision_action(action, x=x, y=y, text=text)

@tool_registry.register(name="swarm_solve")
def swarm_solve(task=None, pedido=None):
    from main import MainApp
    app = MainApp.instance()
    if not app or not hasattr(app, 'chat_window'):
        return "Erro: Aplicativo não inicializado."
    swarm = getattr(app.chat_window.llm_client, 'swarm', None)
    if not swarm:
        return "Erro: Swarm não disponível."
    return swarm.delegate_automatically(task or pedido)

@tool_registry.register(name="generate_image")
def generate_image(prompt=None, output=None):
    from core.image_generator import ImageGenerator
    return ImageGenerator.generate_image(prompt, output)

@tool_registry.register(name="register_user", aliases=["mapeamento_facial"])
def register_user():
    """Captura fotos do usuário para criar um perfil visual de reconhecimento."""
    from core.vision_service import VisionService
    return VisionService().register_user()

@tool_registry.register(name="recognize_user", aliases=["quem_sou_eu"])
def recognize_user():
    """Tenta identificar quem está na frente da câmera agora."""
    from core.vision_service import VisionService
    if VisionService().recognize_user():
        return "Usuário identificado: Jhordan Pastorello."
    return "Não consegui te reconhecer. Você já registrou seu perfil visual?"

@tool_registry.register(name="activate_skill")
def activate_skill(name=None, skill=None):
    from core.skill_manager import SkillManager
    return SkillManager.activate_skill(name or skill)
