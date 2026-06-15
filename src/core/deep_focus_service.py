import time
import threading
import psutil
from datetime import datetime, timedelta

class DeepFocusService:
    """
    Servico de Modo Foco profundo com Pomodoro, bloqueio de notificacoes,
    e adaptacao automatica de hardware.
    """

    # Estados do foco
    STATE_IDLE = "idle"
    STATE_FOCUSED = "focused"
    STATE_BREAK = "break"
    STATE_PAUSED = "paused"

    # Configuracoes padrao
    DEFAULT_POMODORO_MIN = 25
    DEFAULT_BREAK_MIN = 5
    DEFAULT_LONG_BREAK_MIN = 15
    POMODOROS_BEFORE_LONG = 4

    def __init__(self, voice_service=None, hud=None):
        self.voice = voice_service
        self.hud = hud
        self.state = self.STATE_IDLE
        self.current_pomodoro = 0
        self.total_pomodoros = 0
        self._timer_thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Nao pausado por padrao

        # Historico de sessoes
        self.session_history = []
        self._session_start = None

        # Timer real: rastreia o inicio e duracao total da sessao atual
        self._timer_start = None
        self._timer_duration_seconds = 0
        self._timer_elapsed_at_pause = 0

        # Configuracoes de bloqueio
        self._blocked_apps = [
            "com.apple.MobileSMS",  # Messages
            "com.apple.mail",       # Mail
            "com.tinyspeck.slackmacgap",  # Slack
            "com.discordapp.Discord",
            "com.spotify.client",
        ]
        self._original_volume = None
        self._original_brightness = None

        # Callbacks
        self.on_state_change = None
        self.on_pomodoro_complete = None
        self.on_session_complete = None

    def start_focus(self, duration_min=None, task_name=""):
        """Inicia uma sessao de foco Pomodoro."""
        if self.state == self.STATE_FOCUSED:
            return "Ja existe uma sessao de foco ativa."
        
        duration = duration_min or self.DEFAULT_POMODORO_MIN
        self.current_pomodoro += 1
        self.total_pomodoros += 1
        self._session_start = datetime.now()
        self.state = self.STATE_FOCUSED
        self._stop_event.clear()
        self._pause_event.set()

        # Rastreia tempo real do timer
        self._timer_start = time.time()
        self._timer_duration_seconds = duration * 60
        self._timer_elapsed_at_pause = 0

        # Aplica configuracoes de foco
        self._apply_focus_mode(True)

        # Notifica
        self._notify(f"Foco iniciado: {duration}min", f"Sessao #{self.current_pomodoro}" + (f" - {task_name}" if task_name else ""))

        # Inicia timer em background
        self._timer_thread = threading.Thread(
            target=self._pomodoro_timer,
            args=(self._timer_duration_seconds,),
            daemon=True
        )
        self._timer_thread.start()

        return f"Modo foco ativado: {duration} minutos (Pomodoro #{self.current_pomodoro})"

    def stop_focus(self):
        """Para a sessao de foco atual."""
        if self.state == self.STATE_IDLE:
            return "Nenhuma sessao de foco ativa."
        
        self._stop_event.set()
        self._pause_event.set()
        self._apply_focus_mode(False)
        
        session_duration = self._get_session_duration()
        self._record_session(completed=False)
        
        old_state = self.state
        self.state = self.STATE_IDLE
        
        self._notify("Foco encerrado", f"Duracao: {session_duration}")
        
        return f"Sessao de foco encerrada. Duracao: {session_duration}"

    def pause_focus(self):
        """Pausa a sessao de foco."""
        if self.state != self.STATE_FOCUSED:
            return "Nenhuma sessao de foco ativa para pausar."

        self._pause_event.clear()
        # Registra tempo elapsed antes de pausar
        if self._timer_start:
            self._timer_elapsed_at_pause += time.time() - self._timer_start
            self._timer_start = None
        self.state = self.STATE_PAUSED
        self._notify("Foco pausado", "Diga 'continuar' para retomar")
        return "Sessao pausada."

    def resume_focus(self):
        """Retoma a sessao de foco pausada."""
        if self.state != self.STATE_PAUSED:
            return "Nenhuma sessao pausada."

        self._timer_start = time.time()  # Reinicia contagem de tempo ativo
        self._pause_event.set()
        self.state = self.STATE_FOCUSED
        self._notify("Foco retomado", "Continue focado!")
        return "Sessao retomada."

    def get_status(self):
        """Retorna o status atual do foco."""
        if self.state == self.STATE_IDLE:
            return {
                "state": "idle",
                "message": "Nenhum foco ativo",
                "pomodoros_hoje": self.total_pomodoros,
                "historico": self.session_history[-3:] if self.session_history else []
            }
        
        remaining = self._get_remaining_time()
        return {
            "state": self.state,
            "pomodoro_number": self.current_pomodoro,
            "remaining_seconds": remaining,
            "remaining_formatted": self._format_time(remaining),
            "elapsed": self._get_session_duration(),
            "total_pomodoros": self.total_pomodoros
        }

    def _pomodoro_timer(self, duration_seconds):
        """Timer do Pomodoro com suporte a pausa."""
        elapsed = 0
        while elapsed < duration_seconds and not self._stop_event.is_set():
            self._pause_event.wait()  # Bloqueia se pausado
            if self._stop_event.is_set():
                break
            time.sleep(1)
            elapsed += 1
            
            # Avisa a cada 5 minutos restantes
            remaining = duration_seconds - elapsed
            if remaining in [300, 120, 60] and self.voice:
                mins = remaining // 60
                self._notify(f"{mins} minuto{'s' if mins > 1 else ''} restante{'s' if mins > 1 else ''}", "")
        
        if not self._stop_event.is_set():
            self._on_pomodoro_complete()

    def _on_pomodoro_complete(self):
        """Chamado quando um Pomodoro termina."""
        self._record_session(completed=True)
        
        if self.on_pomodoro_complete:
            self.on_pomodoro_complete(self.current_pomodoro)
        
        # Determina se e pausa longa
        is_long = (self.current_pomodoro % self.POMODOROS_BEFORE_LONG == 0)
        break_duration = self.DEFAULT_LONG_BREAK_MIN if is_long else self.DEFAULT_BREAK_MIN
        break_type = "pausa longa" if is_long else "pausa curta"
        
        self.state = self.STATE_BREAK
        self._apply_focus_mode(False)
        
        self._notify(
            f"Pomodoro #{self.current_pomodoro} concluido!",
            f"Hora da {break_type} ({break_duration}min)"
        )
        
        # Timer da pausa
        threading.Thread(
            target=self._break_timer,
            args=(break_duration * 60,),
            daemon=True
        ).start()

    def _break_timer(self, duration_seconds):
        """Timer da pausa entre Pomodoros."""
        elapsed = 0
        while elapsed < duration_seconds and not self._stop_event.is_set():
            time.sleep(1)
            elapsed += 1
        
        if not self._stop_event.is_set():
            self.state = self.STATE_IDLE
            self._notify("Pausa terminada!", "Pronto para novo foco?")

    def _apply_focus_mode(self, enabled):
        """Aplica ou remove as configuracoes de modo foco."""
        try:
            from core.hardware_manager import HardwareManager
            
            if enabled:
                # Salva estado atual do volume (nao da bateria)
                try:
                    import subprocess
                    result = subprocess.run(
                        ['osascript', '-e', 'output volume of (get volume settings)'],
                        capture_output=True, text=True, timeout=5
                    )
                    self._original_volume = int(result.stdout.strip()) if result.stdout.strip() else None
                except Exception:
                    self._original_volume = None
                
                # Reduz volume e ativa Nao Perturbe
                HardwareManager.set_volume(0)
                HardwareManager.send_command_to_swift({"action": "toggle_dnd"})
            else:
                # Restaura volume
                if self._original_volume is not None:
                    HardwareManager.set_volume(self._original_volume)
                else:
                    HardwareManager.set_volume(50)
                
                # Desativa Nao Perturbe
                HardwareManager.send_command_to_swift({"action": "toggle_dnd"})
        except Exception:
            pass

    def _record_session(self, completed):
        """Registra a sessao no historico."""
        if self._session_start:
            duration = (datetime.now() - self._session_start).total_seconds()
            self.session_history.append({
                "start": self._session_start.isoformat(),
                "duration_seconds": duration,
                "completed": completed,
                "pomodoro_number": self.current_pomodoro
            })

    def _get_session_duration(self):
        """Retorna a duracao da sessao atual formatada."""
        if self._session_start:
            elapsed = (datetime.now() - self._session_start).total_seconds()
            return self._format_time(elapsed)
        return "0:00"

    def _get_remaining_time(self):
        """Retorna tempo restante em segundos (baseado no timer real)."""
        if self.state == self.STATE_IDLE:
            return 0
        if self.state == self.STATE_PAUSED:
            # Quando pausado, calcula baseado no elapsed acumulado
            elapsed = self._timer_elapsed_at_pause
        elif self._timer_start:
            elapsed = self._timer_elapsed_at_pause + (time.time() - self._timer_start)
        else:
            elapsed = self._timer_elapsed_at_pause

        remaining = max(0, self._timer_duration_seconds - elapsed)
        return int(remaining)

    def _format_time(self, seconds):
        """Formata segundos em MM:SS."""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins}:{secs:02d}"

    def _notify(self, title, message):
        """Notifica via HUD e voz."""
        if self.hud:
            try:
                self.hud.display_signal.emit(title, "FOCUS" if self.state == self.STATE_FOCUSED else "IDLE", 3000)
            except Exception:
                pass
        if self.voice:
            try:
                full_msg = f"{title}. {message}" if message else title
                self.voice.speak(full_msg)
            except Exception:
                pass

    def get_daily_summary(self):
        """Retorna resumo do foco do dia."""
        today = datetime.now().date()
        today_sessions = [
            s for s in self.session_history
            if datetime.fromisoformat(s["start"]).date() == today
        ]
        
        total_time = sum(s["duration_seconds"] for s in today_sessions)
        completed = sum(1 for s in today_sessions if s["completed"])
        
        return {
            "date": today.isoformat(),
            "total_sessions": len(today_sessions),
            "completed_pomodoros": completed,
            "total_focus_minutes": int(total_time / 60),
            "average_session": int(total_time / len(today_sessions) / 60) if today_sessions else 0
        }
