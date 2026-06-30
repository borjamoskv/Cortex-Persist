import pytest
import json
from babylon60.swarm.flujo_glorioso import DecaCoreOrchestrator
from babylon60.engine.causal.belief_objects import BeliefObject

def test_flujo_glorioso_concepcion():
    orchestrator = DecaCoreOrchestrator()
    input_data = {"idea": "glorious concept"}
    result = orchestrator.concepcion(input_data)
    
    assert isinstance(result, BeliefObject)
    assert result.payload.context_hash == "concepcion_ctx"
    assert json.loads(result.payload.content) == input_data

def test_flujo_glorioso_full_pipeline():
    orchestrator = DecaCoreOrchestrator()
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
        result = phase_func(data)
        assert isinstance(result, BeliefObject)
        assert "ctx" in result.payload.context_hash
        data = json.loads(result.payload.content)
