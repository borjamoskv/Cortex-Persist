import pytest
import asyncio
from babylon60.agents.builtins.epistemic_validator import EpistemicValidatorAgent

from babylon60.agents.manifest import AgentManifest
from unittest.mock import MagicMock

@pytest.fixture
def agent():
    manifest = AgentManifest(agent_id="test_epistemic", purpose="testing")
    bus = MagicMock()
    return EpistemicValidatorAgent(manifest=manifest, bus=bus)

@pytest.mark.asyncio
async def test_deterministic_observation(agent):
    result = agent._deterministic_classify("El archivo main.py tiene 150 líneas registradas.")
    assert result["type"] == "observation"
    assert result["confidence"] >= 0.9

@pytest.mark.asyncio
async def test_deterministic_hypothesis(agent):
    result = agent._deterministic_classify("Si migramos a Rust, la seguridad aumentará.")
    assert result["type"] == "hypothesis"
    assert result["confidence"] >= 0.9

@pytest.mark.asyncio
async def test_deterministic_inference(agent):
    result = agent._deterministic_classify("Probablemente la función tenga bugs.")
    assert result["type"] == "inference"
    assert result["confidence"] >= 0.9
    assert result["depends_on"] == []

@pytest.mark.asyncio
async def test_deterministic_mixed(agent):
    result = agent._deterministic_classify("El archivo tiene 500 líneas por lo que probablemente es complejo.")
    assert result["type"] == "mixed"
    assert result["confidence"] < 0.9

@pytest.mark.asyncio
async def test_validate_claim_pure_inference_hard_fail(agent):
    with pytest.raises(ValueError, match="Ontological Contradiction"):
        await agent._validate_claim({"claim": "Sabemos que el sistema es seguro."})

@pytest.mark.asyncio
async def test_validate_claim_mixed_resolved(agent):
    result = await agent._validate_claim({"claim": "El archivo tiene 500 líneas, por lo que probablemente es complejo."})
    assert result["status"] == "validated"
    nodes = result["epistemic_nodes"]
    assert len(nodes) == 2
    assert nodes[0]["type"] == "observation"
    assert nodes[1]["type"] == "inference"
    assert "obs_auto_01" in nodes[1]["depends_on"]
