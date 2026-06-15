import pytest
import time
from core.deep_focus_service import DeepFocusService


class TestDeepFocusService:
    def setup_method(self):
        self.service = DeepFocusService()

    def test_initial_state(self):
        assert self.service.state == DeepFocusService.STATE_IDLE
        assert self.service.current_pomodoro == 0

    def test_get_remaining_time_idle(self):
        assert self.service._get_remaining_time() == 0

    def test_start_focus(self):
        result = self.service.start_focus(duration_min=1)
        assert "Modo foco ativado" in result
        assert self.service.state == DeepFocusService.STATE_FOCUSED
        assert self.service._timer_start is not None
        assert self.service._timer_duration_seconds == 60
        self.service.stop_focus()

    def test_stop_focus(self):
        self.service.start_focus(duration_min=1)
        result = self.service.stop_focus()
        assert "encerrada" in result
        assert self.service.state == DeepFocusService.STATE_IDLE

    def test_pause_resume(self):
        self.service.start_focus(duration_min=1)
        self.service.pause_focus()
        assert self.service.state == DeepFocusService.STATE_PAUSED
        assert self.service._timer_start is None
        self.service.resume_focus()
        assert self.service.state == DeepFocusService.STATE_FOCUSED
        assert self.service._timer_start is not None
        self.service.stop_focus()

    def test_double_start(self):
        self.service.start_focus(duration_min=1)
        result = self.service.start_focus(duration_min=1)
        assert "ja existe" in result.lower()
        self.service.stop_focus()

    def test_get_status(self):
        status = self.service.get_status()
        assert status["state"] == "idle"
        assert "pomodoros_hoje" in status

    def test_daily_summary(self):
        summary = self.service.get_daily_summary()
        assert "total_sessions" in summary
        assert "completed_pomodoros" in summary
