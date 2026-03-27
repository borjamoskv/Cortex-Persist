import time
from unittest.mock import AsyncMock, patch

import pytest

from cortex.agents.builtins.cazarecompensas_agent import BountyState, CazarecompensasAgent
from cortex.agents.manifest import AgentManifest


@pytest.fixture
def agent():
    manifest = AgentManifest(
        agent_id="test_caza",
        purpose="Test"
    )
    return CazarecompensasAgent(manifest=manifest, bus=None)


def test_evaluate_thermodynamics_accepted(agent):
    bounty = {
        "id": "ALG-100",
        "title": "Fix something",
        "platform": "Algora",
        "difficulty_score": 2.0,
        "reward_usd": 1000.0,
        "context_lines": 500,
    }

    res = agent._evaluate_thermodynamics(bounty)

    assert res["exergy_estimate"] == 1000.0
    assert res["ratio"] > agent._thermodynamic_threshold
    assert res["accepted"] is True
    assert "Justificación" in res["justification"]


def test_evaluate_thermodynamics_rejected(agent):
    bounty = {
        "id": "ALG-200",
        "title": "Hard small bounty",
        "platform": "Algora",
        "difficulty_score": 8.0,
        "reward_usd": 50.0,
        "context_lines": 1000,
    }

    res = agent._evaluate_thermodynamics(bounty)

    assert res["accepted"] is False
    assert res["ghost_vector_penalty"] == 500.0
    assert res["meta_stability_risk"] == 256.0


@pytest.mark.asyncio
async def test_execute_extraction_yield_deferred(agent):
    bounty = {
        "id": "ALG-400",
        "title": "Extraction Test",
        "platform": "Algora",
        "difficulty_score": 1.0,
        "reward_usd": 1000.0,
        "context_lines": 500,
    }
    evaluation = agent._evaluate_thermodynamics(bounty)

    result = await agent._execute_extraction(bounty, evaluation)

    assert "final_yield_applied" in result
    # It should NOT accumulate yield immediately, deferred to settlement
    assert float(agent._total_exergy_extracted) == 0.0


@pytest.mark.asyncio
async def test_verify_settlements(agent):
    agent._pending_settlements.append({
        "id": "ALG-999",
        "final_yield_applied": 1500.0
    })

    await agent._verify_settlements()

    assert float(agent._total_exergy_extracted) == 1500.0
    assert agent._bounty_states.get("ALG-999") == BountyState.SETTLED
    assert len(agent._pending_settlements) == 0


@pytest.mark.asyncio
async def test_circuit_breaker(agent):
    # Simulate 3 consecutive failures
    agent._consecutive_failures = 3
    penalty = 300.0 * (2.0 ** 0)
    agent._circuit_breaker_until = time.time() + penalty

    with patch.object(agent, "_scan_for_bounties", new_callable=AsyncMock) as scan_mock:
        await agent._run_autonomous_hunt()
        scan_mock.assert_not_called()  # Breaker active, scan aborted


@pytest.mark.asyncio
async def test_quarantine_immune_response(agent):
    bounty = {
        "id": "ALG-500",
        "title": "Malicious Bounty",
        "platform": "Algora",
        "difficulty_score": 9.0,
        "reward_usd": 10000.0,
        "context_lines": 10000,
    }

    with patch.object(agent, "_evaluate_thermodynamics", return_value={"accepted": True, "ratio": 10.0}), \
         patch.object(agent, "_scan_for_bounties", return_value=[bounty]), \
         patch.object(agent, "_execute_extraction", new_callable=AsyncMock) as execute_mock:

        await agent._run_autonomous_hunt()

        execute_mock.assert_not_called()
        # Even if quarantined, state transitions to DISCOVERED so we don't spam it unless state clears
        assert agent._bounty_states.get("ALG-500") == BountyState.DISCOVERED
