# [C5-REAL] Exergy-Maximized

import pytest
from unittest.mock import AsyncMock, MagicMock
from cortex_extensions.trust.c8_reputation_metabolism import ReputationMetabolism
from cortex_extensions.trust.bayesian import TrustUpdate, Signal
from cortex_extensions.hypervisor.belief_object import BeliefObject, BeliefConfidence

@pytest.mark.asyncio
async def test_reputation_metabolism_genesis_and_mutation():
    """Test the creation and ledger persistence of C8 Reputation BeliefObjects."""
    engine = AsyncMock()
    
    # Simula base vacía: no hay reputación previa
    engine.recall.return_value = []
    
    metabolism = ReputationMetabolism(engine)
    
    # 1. Génesis
    belief = await metabolism.register_interaction(
        entity_id="agent_x",
        interaction_type="payload_delivery",
        signal=Signal.CONFIRM,
        project="test_project",
    )
    
    assert belief.confidence == BeliefConfidence.C3_PROBABLE
    assert "Reputación base" in belief.content
    
    # Verifica que se guardó la mutación en el ledger
    engine.store.assert_called_once()
    store_kwargs = engine.store.call_args.kwargs
    assert store_kwargs["fact_type"] == "reputation_mutation"
    assert store_kwargs["meta"]["entity_id"] == "agent_x"
    assert store_kwargs["meta"]["interaction_type"] == "payload_delivery"
    assert store_kwargs["meta"]["signal"] == "confirm"
    
    # 2. Mutación (Entidad ya existe)
    engine.store.reset_mock()
    
    # Creamos un fact simulado devuelto por engine.recall
    mock_fact = MagicMock()
    mock_fact.id = 42
    mock_fact.meta = {"belief_object": belief.to_dict()}
    engine.recall.return_value = [mock_fact]
    
    # Simulamos el BayesianTrustUpdater interceptando la llamada
    mock_updater = AsyncMock()
    mock_updater.update.return_value = TrustUpdate(
        fact_id=42,
        signal="confirm",
        old_confidence="C3",
        new_confidence="C4",
        old_consensus_score=0.5,
        new_consensus_score=0.7,
        alpha=10.0,
        beta=2.0,
        posterior_mean=0.8,
        posterior_variance=0.01,
        confidence_changed=True,
    )
    metabolism._updater = mock_updater
    
    mutated_belief = await metabolism.register_interaction(
        entity_id="agent_x",
        interaction_type="data_enrichment",
        signal=Signal.CONFIRM,
        project="test_project",
    )
    
    assert mutated_belief.confidence.value == "C4"
    assert mutated_belief.provenance.entries[-1].action == "revised"
    
    engine.store.assert_called_once()
    store_kwargs2 = engine.store.call_args.kwargs
    assert store_kwargs2["fact_type"] == "reputation_mutation"
    assert "C3 -> C4" in store_kwargs2["content"]
