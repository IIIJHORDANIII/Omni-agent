import pytest
from unittest.mock import MagicMock, patch
from core.evolution_service import EvolutionService

@pytest.fixture
def evolution_service():
    mock_llm = MagicMock()
    service = EvolutionService(llm_manager=mock_llm)
    service.skills_dir = "/tmp/test_skills"
    return service

def test_evaluate_and_evolve_skip(evolution_service):
    # Mock LLM to return SKIP
    evolution_service.llm.generate_command.return_value = "SKIP"
    
    result = evolution_service.evaluate_and_evolve(
        "Abrir calculadora", 
        "Executei open_app('Calculator')", 
        "Calculadora aberta"
    )
    
    assert result is False
    evolution_service.llm.generate_command.assert_called_once()

def test_evaluate_and_evolve_success(evolution_service, tmp_path):
    # Setup tmp skills dir
    test_skills_dir = tmp_path / "skills"
    test_skills_dir.mkdir()
    evolution_service.skills_dir = str(test_skills_dir)
    
    # Mock LLM to return a new skill
    skill_content = """# Habilidade: Teste Complexo
Use esta habilidade quando...
## Processo Obrigatório
1. Passo A
2. Passo B
"""
    evolution_service.llm.generate_command.return_value = skill_content
    
    result = evolution_service.evaluate_and_evolve(
        "Refatorar auth", 
        "Li auth.py, removi any, rodei pytest", 
        "Auth refatorado com 100% cobertura"
    )
    
    assert result == "teste_complexo"
    skill_file = test_skills_dir / "teste_complexo" / "SKILL.md"
    assert skill_file.exists()
    assert skill_file.read_text() == skill_content
