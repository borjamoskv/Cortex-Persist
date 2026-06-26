import pytest
from unittest.mock import AsyncMock, MagicMock

from cortex.guards.causal_closure_guard import CausalClosureGuard, SwarmProposal
from cortex.engine.uncategorized.entropy import EntropyAnnihilator
from cortex.engine.uncategorized.crystallizer import AutoCrystallizer

# 1. Test: Cheap Hallucination
def test_cheap_hallucination():
    """
    Test: Enviar una propuesta puramente narrativa de bajo coste.
    Expectativa: Debe fallar la clausura causal y lanzar RuntimeError.
    """
    guard = CausalClosureGuard(min_token_threshold=50000)
    
    # Propuesta narrativa sin evidencia estructural
    proposal = SwarmProposal(
        agent_id="agent_1",
        mission_statement="Narrative task",
        content="I have mathematically verified that the system works perfectly and everything is fine.",
        token_cost=10  # Extremadamente barato
    )
    
    with pytest.raises(RuntimeError, match="Causal Closure Failure|AX-VIII Violation|Causal Closure"):
        guard.verify_closure(proposal)

# 2. Test: Self-Certified Deletion
def test_self_certified_deletion(tmp_path):
    """
    Test: Intentar purgar una capa arquitectónica inyectando confidence = 1.0.
    Expectativa: Debe requerir prueba estructural (SAGA/evidencia explícita) en lugar de auto-aprobarse probabilísticamente.
    """
    dummy_file = tmp_path / "dummy_sink.py"
    dummy_file.write_text("class EmptyAbstraction:\\n    pass\\n")
    
    annihilator = EntropyAnnihilator(str(tmp_path))
    annihilator.scan_ecosystem = MagicMock(return_value=[(str(dummy_file), 0.9)])
    
    # In the new code, purge_energy_sinks should raise an error if invoked purely with confidence.
    with pytest.raises(RuntimeError, match="SAGA-1|Evidence required|Confidence > Evidence"):
        annihilator.purge_energy_sinks(threshold=0.8, confidence=1.0)

# 3. Test: Crystallization Collapse
@pytest.mark.asyncio
async def test_crystallization_collapse():
    """
    Test: Forzar un fallo del LLM en la compresión entrópica.
    Expectativa: Lanza RuntimeError en vez de tragar la entropía cruda.
    """
    mock_llm = AsyncMock()
    # Mockeamos el LLM para que devuelva contenido vacío (falla al comprimir)
    mock_llm.generate.return_value = ""
    
    crystallizer = AutoCrystallizer(llm_manager=mock_llm)
    
    raw_content = "This is a very long, conversational, extremely bloated string that has no value but just adds thermal noise to the ecosystem..."
    
    with pytest.raises(RuntimeError, match="SAGA-1|entropy"):
        await crystallizer.crystallize(raw_content)

