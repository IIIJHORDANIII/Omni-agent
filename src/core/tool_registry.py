import functools

class ToolRegistry:
    """
    Registro dinâmico de ferramentas para o Agente.
    Substitui o bloco monolítico if/elif no ToolDispatcher.
    """
    _tools = {}

    @classmethod
    def register(cls, name=None, aliases=None):
        """Decorador para registrar uma função como ferramenta."""
        def decorator(func):
            tool_name = name or func.__name__
            cls._tools[tool_name] = func
            if aliases:
                for alias in aliases:
                    cls._tools[alias] = func
            return func
        return decorator

    @classmethod
    def get_tool(cls, name):
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls):
        return list(cls._tools.keys())

# Instância global
tool_registry = ToolRegistry()
