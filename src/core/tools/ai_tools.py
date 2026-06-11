from core.tool_registry import tool_registry

@tool_registry.register(name="analyze_screen", aliases=["describe_screen"])
def analyze_screen():
    from core.vision_service import VisionService
    return VisionService().describe_screen()

@tool_registry.register(name="vision_action")
def vision_action(action=None, x=None, y=None, text=None):
    from main import MainApp
    computer = MainApp.instance().chat_window.llm_client.computer
    return computer.vision_action(action, x=x, y=y, text=text)

@tool_registry.register(name="swarm_solve")
def swarm_solve(task=None, pedido=None):
    from main import MainApp
    swarm = MainApp.instance().chat_window.llm_client.swarm
    return swarm.delegate_automatically(task or pedido)

@tool_registry.register(name="generate_image")
def generate_image(prompt=None, output=None):
    from core.image_generator import ImageGenerator
    return ImageGenerator.generate_image(prompt, output)

@tool_registry.register(name="activate_skill")
def activate_skill(name=None, skill=None):
    from core.skill_manager import SkillManager
    return SkillManager.activate_skill(name or skill)
