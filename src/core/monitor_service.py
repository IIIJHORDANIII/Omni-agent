import threading
import time
import base64
from core.context_service import ContextService
from core.vision_service import VisionService

class MonitorService:
    def __init__(self, llm_client, voice_service, memory_client, hud=None):
        self.llm_client = llm_client
        self.voice = voice_service
        self.memory = memory_client
        self.vision = None # Será injetado pelo main.py
        self.hud = hud
        self.running = False
        self.thread = None
        # Intervalo entre pensamentos proativos (segundos) - Reduzido para ser menos intrusivo
        self.think_interval = 3600  # 1 hora por padrão (Oracle Mode)
        # Intervalo para o Watchdog Visual rápido (segundos)
        self.watchdog_interval = 600 # 10 minutos (Evita uso excessivo de hardware)

    def start(self):
        """Inicia o ciclo de monitoramento proativo."""
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("Sentinela: Monitoramento visual e de contexto ativado.")

    def stop(self):
        self.running = False

    def _run(self):
        # Aguarda o sistema estabilizar (45s) para evitar SegFault/Trace Trap por carga de modelos
        time.sleep(45)
        last_think_time = 0
        
        while self.running:
            current_time = time.time()
            
            try:
                # 1. Watchdog Visual (Rápido)
                # Verifica se há algo urgente na tela que precise de ação imediata
                self._quick_visual_scan()
                
                # 2. Pensamento Estratégico (Lento)
                # O agente olha para o contexto geral e para a imagem da tela para dar sugestões
                if current_time - last_think_time > self.think_interval:
                    self._think_strategically()
                    last_think_time = current_time
                    
            except Exception as e:
                print(f"Erro no loop do Monitor de Sistema (Oracle Mode): {e}")
            
            time.sleep(self.watchdog_interval)

    def _quick_visual_scan(self):
        """Usa visão computacional tradicional para detectar elementos críticos."""
        from core.visual_watchdog import VisualWatchdog
        VisualWatchdog.scan()

    def _think_strategically(self):
        """Usa a LLM com Visão Real e Telemetria para análise Oracle."""
        print("Sentinela (Oracle) analisando ambiente...")
        
        # 1. Coleta Contexto e Telemetria Oracle
        ctx = ContextService.get_full_context()
        sys = ctx['system']
        active_app = ctx['active_window'].lower()
        
        # Alerta Oracle: Processos pesados
        if sys.get('top_processes'):
            proc = sys['top_processes'][0]
            if proc['cpu_percent'] > 80:
                msg = f"Senhor, o processo {proc['name']} está consumindo {proc['cpu_percent']}% da CPU. Deseja que eu encerre?"
                self.voice.speak(msg)
                self.hud.display_signal.emit("ALERTA DE CARGA", "THINKING", 5000)
                return

        # 2. Visão Computacional (Se disponível)
        vision_desc = ""
        if self.vision:
            vision_desc = self.vision.describe_screen("Resuma o que o usuário está fazendo agora em uma frase.")

        prompt = f"""Você é o OMNISCIENT (Oracle Mode).
ANALISE O AMBIENTE:
- App Ativo: {active_app}
- CPU: {sys['cpu']}%
- Visão Real: {vision_desc}

SUA TAREFA:
Se houver algo útil a dizer ou sugerir (ex: 'Você está no VS Code, quer que eu rode os testes?'), fale.
Se estiver tudo normal, responda 'SILENCIO'.
Seja extremamente breve.
"""
        # O llm_client processa o pensamento estratégico baseado na visão do Qwen2-VL
        # Usamos uma mensagem de sistema injetada para simular o comportamento Oracle
        messages = [{"role": "user", "content": prompt}]
        response = self.llm_client.chat(messages)
        
        clean_response = response.strip()
        
        # Filtro robusto: Se for JSON ou contiver SILENCIO, ignoramos
        if "{" in clean_response or "SILENCIO" in clean_response.upper() or len(clean_response) < 10:
            return

        print(f"OMNISCIENT PROATIVO: {clean_response}")
        self.hud.display_signal.emit(f"SUGESTÃO: {clean_response}", "PROACTIVE", 7000)
        self.voice.speak(clean_response)

    def set_interval(self, seconds):
        self.think_interval = seconds
