import threading

class ServiceRegistry:
    """
    Registro central de serviços para desacoplar o MainApp.
    Permite o carregamento preguiçoso (lazy-loading) e descoberta dinâmica.
    """
    _instance = None
    _lock = threading.Lock()
    _services = {}

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ServiceRegistry, cls).__new__(cls)
            return cls._instance

    @classmethod
    def register(cls, name, service_instance):
        """Registra uma instância de serviço já inicializada."""
        cls._services[name] = service_instance
        print(f"Registry: Serviço '{name}' registrado.")

    @classmethod
    def get(cls, name):
        """Recupera um serviço pelo nome."""
        return cls._services.get(name)

    @classmethod
    def list_services(cls):
        return list(cls._services.keys())

# Instância global para facilitar o acesso
registry = ServiceRegistry()
