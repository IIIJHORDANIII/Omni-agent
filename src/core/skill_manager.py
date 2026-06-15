import os

class SkillManager:
    """
    Gerencia a ativação de habilidades de engenharia de elite (inspirado no agent-skills).
    Transforma arquivos Markdown em diretrizes de sistema em tempo real.
    """
    
    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
    ACTIVE_SKILL = None

    @staticmethod
    def get_skill_content(skill_name):
        """Busca o conteúdo de um arquivo SKILL.md pelo nome da pasta."""
        skill_path = os.path.join(SkillManager.BASE_DIR, skill_name, "SKILL.md")
        
        if not os.path.exists(skill_path):
            return None
            
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Erro ao carregar habilidade {skill_name}: {e}")
            return None

    @staticmethod
    def activate_skill(skill_name):
        """Define a habilidade ativa para a sessão atual."""
        content = SkillManager.get_skill_content(skill_name)
        if content:
            SkillManager.ACTIVE_SKILL = {
                "name": skill_name,
                "content": content
            }
            return f"Habilidade '{skill_name}' ATIVADA. Seguindo protocolos de elite."
        return f"Habilidade '{skill_name}' não encontrada."

    @staticmethod
    def get_active_skill_prompt():
        """Retorna o prompt da habilidade ativa para ser injetado no sistema."""
        if SkillManager.ACTIVE_SKILL:
            return f"\n\n[HABILIDADE ATIVA: {SkillManager.ACTIVE_SKILL['name'].upper()}]\n" + \
                   f"{SkillManager.ACTIVE_SKILL['content']}\n"
        return ""
