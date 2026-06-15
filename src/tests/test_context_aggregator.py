import pytest
from core.context_aggregator import ContextAggregator


class TestContextAggregator:
    def setup_method(self):
        self.aggregator = ContextAggregator()

    def test_fuzzy_match_exact(self):
        assert self.aggregator._fuzzy_match("vision_service.py", "src/core/vision_service.py")

    def test_fuzzy_match_parts(self):
        assert self.aggregator._fuzzy_match("vision_service", "Found issue: refactor vision_service logic")

    def test_fuzzy_match_no_match(self):
        assert not self.aggregator._fuzzy_match("unrelated_file.py", "Some unrelated text about deployment")

    def test_get_context_unknown(self):
        result = self.aggregator.get_context_for_file("unknown")
        assert result is None

    def test_get_context_none(self):
        result = self.aggregator.get_context_for_file(None)
        assert result is None

    def test_get_context_returns_dict(self):
        result = self.aggregator.get_context_for_file("/src/core/test.py")
        assert "file" in result
        assert result["file"] == "test.py"
        assert "linear" in result
        assert "github" in result
