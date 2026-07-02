import pytest
import json
from unittest.mock import AsyncMock
from babylon60.swarm.flujo_glorioso import DecaCoreOrchestrator
from babylon60.engine.causal.belief_objects import BeliefObject
from babylon60.database.belief_store import BeliefStore

@pytest.fixture
def mock_store():
    store = AsyncMock(spec=BeliefStore)
    store.insert_belief = AsyncMock(return_value=1)
    return store

@pytest.mark.asyncio
async def test_flujo_glorioso_concepcion(mock_store):
    orchestrator = DecaCoreOrchestrator(mock_store)
    input_data = {"idea": "glorious concept"}
    result = await orchestrator.concepcion(input_data)
    
    assert isinstance(result, BeliefObject)
    assert result.payload.context_hash == "concepcion_ctx"
    assert json.loads(result.payload.content) == input_data
    mock_store.insert_belief.assert_awaited_once()

@pytest.mark.asyncio
async def test_flujo_glorioso_full_pipeline(mock_store):
    orchestrator = DecaCoreOrchestrator(mock_store)
    data = {"project": "omega"}
    
    phases = [
        orchestrator.concepcion,
        orchestrator.visualizacion,
        orchestrator.sonido,
        orchestrator.animacion,
        orchestrator.voz,
        orchestrator.lipsync,
        orchestrator.edicion,
        orchestrator.vfx,
        orchestrator.upscaling,
        orchestrator.despliegue
    ]
    
    for phase_func in phases:
        result = await phase_func(data)
        assert isinstance(result, BeliefObject)
        assert "ctx" in result.payload.context_hash
        data = json.loads(result.payload.content)
        
    assert mock_store.insert_belief.call_count == 10
