from unittest.mock import patch

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from babylon60.swarm.flujo_glorioso import DecaCoreOrchestrator
from babylon60.engine.causal.belief_objects import BeliefObject
from babylon60.database.belief_store import BeliefStore
from babylon60.embeddings.local import LocalEmbedder

@pytest.fixture
def mock_store():
    return AsyncMock(spec=BeliefStore)

@pytest.fixture
def mock_embedder():
    embedder = MagicMock(spec=LocalEmbedder)
    embedder.embed.return_value = [0.0] * 384
    return embedder

@pytest.mark.asyncio
@patch("babylon60.engine.core.ultrathink_physics.UltrathinkPhysicsEngine.calculate_exergy_yield")
async def test_flujo_glorioso_concepcion(mock_exergy, mock_store, mock_embedder):
    mock_exergy.return_value = 1.0 # Simulate high exergy
    orchestrator = DecaCoreOrchestrator(mock_store, mock_embedder)
    input_data = {"idea": "glorious concept"}
    result = await orchestrator.concepcion(input_data)
    
    assert isinstance(result, BeliefObject)
    assert result.provenance.source_hash == "concepcion_ctx"
    
    output_data = json.loads(result.proposition)
    assert output_data["idea"] == "glorious concept"
    assert output_data["concepcion_completed"] is True
    assert output_data["agent_role"] == "Musa"
    mock_store.insert_belief.assert_awaited_once()
    mock_embedder.embed.assert_called_once()

@pytest.mark.asyncio
@patch("babylon60.engine.core.ultrathink_physics.UltrathinkPhysicsEngine.calculate_exergy_yield")
async def test_flujo_glorioso_full_pipeline(mock_exergy, mock_store, mock_embedder):
    mock_exergy.return_value = 1.0 # Simulate high exergy to prevent Apoptosis
    orchestrator = DecaCoreOrchestrator(mock_store, mock_embedder)
    trajectory = await orchestrator.execute_genesis("omega project")
    
    assert len(trajectory) == 10
    
    # Assert causality: The final state must have accumulated completions
    final_belief = trajectory[-1]
    final_data = json.loads(final_belief.proposition)
    
    assert final_data["idea"] == "omega project"
    assert final_data["concepcion_completed"] is True
    assert final_data["despliegue_completed"] is True
    assert final_data["agent_role"] == "Comandante"
    
    assert mock_store.insert_belief.call_count == 10
