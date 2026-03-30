import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from cortex.engine.kinetic_env import KineticEnv
from cortex.engine.isolation import IsolationLevel


@pytest.fixture
def env():
    # Use LOCAL isolation for tests to avoid needing full external containers
    return KineticEnv(tenant_id="test_tenant", level=IsolationLevel.LOCAL)


@pytest.mark.asyncio
async def test_kinetic_env_step_exergy(env):
    """Verify that KineticEnv spins up sandbox, measures TTFT, and checks Exergy."""
    
    with patch("cortex.engine.kinetic_env.get_default_ledger") as mock_get_ledger:
        mock_ledger = AsyncMock()
        mock_get_ledger.return_value = mock_ledger
        
        # Override the ledger inside the instantiated env
        env.ledger = mock_ledger
        
        res_reset = await env.reset()
        assert "workspace_id" in res_reset
        assert res_reset["step"] == 0
        
        # Provide a high-density payload to pass Maxwell
        payload = "A very dense and meaningful cognitive payload. " * 10
        action = "echo KINETIC_OMEGA"
        
        obs = await env.step(action, payload)
        
        # Verify Observation shape
        assert obs["step"] == 1
        assert "KINETIC_OMEGA" in obs["output"]
        assert obs["status"] == "success"
        
        # Verify thermodynamic measurement
        assert obs["duration"] > 0.0 # TTFT measured
        assert obs["exergy_loss"] == 0 # Passed Maxwell
        
        # Verify Ledger Persistence Causality
        mock_ledger.store_fact.assert_called()
        call_args = mock_ledger.store_fact.call_args[1]
        assert "Step 1 executed: echo" in call_args["fact"]
        assert call_args["metadata"]["action"] == action
        
        await env.close()
