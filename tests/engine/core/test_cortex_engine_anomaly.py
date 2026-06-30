import pytest
from unittest.mock import patch

from babylon60.engine.core.cortex_engine import CortexEngine


@pytest.mark.asyncio
async def test_cortex_engine_report_anomaly_trigger_ultrathink():
    """
    Test that CortexEngine properly delegates to UltraThinkPhysicsEngine
    and mutates the state when an anomaly with high blast radius is detected.
    """
    engine = CortexEngine()

    # A dependency graph simulating a deep blast radius (>= 3)
    # Target node: "cortex_engine"
    dependency_graph = {
        "cortex_engine": ["ledger", "auth", "memory"],
        "ledger": ["crypto", "db"],
        "crypto": ["vault"],
        "vault": [],
    }

    # We mock the dispatcher to prevent actual git commits during testing
    with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_dispatch:
        # report_anomaly automatically uses the formula with high entropy defaults
        result = await engine.report_anomaly(
            epicenter_node="cortex_engine", dependency_graph=dependency_graph, execution_time=0.001
        )

        # Validation 1: The anomaly should trigger UltraThink (return True)
        assert result is True

        # Validation 2: The system state MUST collapse into APEX_STATE
        assert engine.system_state == "APEX_STATE"

        # Validation 3: Sentinel dispatched critical alert
        mock_dispatch.assert_called_once()
        args, kwargs = mock_dispatch.call_args
        assert args[0] == "OP_GIT_SENTINEL"
        assert "P0 Singularity Auto-Triggered" in kwargs["commit_msg"]


@pytest.mark.asyncio
async def test_cortex_engine_report_anomaly_ignored_if_small_radius():
    """
    Test that CortexEngine ignores anomalies with low blast radius (< 3).
    """
    engine = CortexEngine()

    # Very small dependency graph (radius = 2)
    dependency_graph = {"utils": ["strings"], "strings": []}

    with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_dispatch:
        result = await engine.report_anomaly(
            epicenter_node="utils", dependency_graph=dependency_graph, execution_time=0.1
        )

        # Validation 1: The anomaly should NOT trigger UltraThink (return False)
        assert result is False

        # Validation 2: The system state remains default (ACTIVE)
        assert engine.system_state == "ACTIVE"

        # Validation 3: No sentinel dispatched
        mock_dispatch.assert_not_called()
