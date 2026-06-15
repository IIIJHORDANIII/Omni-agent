import threading
import time
from core.execution_service import ExecutionService

class TimeGuardService:
    """
    Monitora o calendário e fornece briefings automáticos antes de reuniões.
    """
    def __init__(self, voice_service, llm_client):
        self.voice = voice_service
        self.llm = llm_client
        self.running = False
        self.announced_events = set()

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        print("Time-Guard: Monitoramento de reuniões ativado.")

    def _monitor_loop(self):
        while self.running:
            try:
                # 1. Busca eventos do calendário
                events_raw = ExecutionService.get_calendar_events()
                if "Nenhum" in events_raw:
                    time.sleep(300) # Dorme 5 min se não houver nada
                    continue

                # 2. Analisa proximidade (Lógica simples de texto por enquanto)
                # Exemplo: "[Calendar] Reunião às Wed Jun 10 10:30:00 2026"
                current_time = time.time()
                
                # Para simplificar na V1, enviamos para o LLM analisar o que é urgente
                self._check_with_llm(events_raw)
                
                time.sleep(600) # Checa a cada 10 min
            except Exception as e:
                print(f"Time-Guard Erro: {e}")
                time.sleep(60)

    def _check_with_llm(self, events_text):
        prompt = f"""Analise estes eventos de hoje:
        {events_text}
        
        Hora atual: {time.strftime('%H:%M')}
        
        Sua tarefa:
        1. Identifique se há alguma reunião começando nos próximos 15 minutos.
        2. Se houver, gere um briefing de voz curto e elegante avisando o usuário.
        3. Se não houver nada urgente, responda apenas 'IDLE'.
        """
        
        briefing = self.llm.chat([{"role": "user", "content": prompt}])
        
        if briefing and "IDLE" not in briefing.upper() and briefing not in self.announced_events:
            self.voice.speak(briefing)
            self.announced_events.add(briefing)
