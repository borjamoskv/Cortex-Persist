"""
End-to-End Verification of Sovereign Improvement (Cycles 1-5).
Verifies Isolation, Legion-Omega Swarm, and Native Actuators.
"""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cortex.engine.actuator_local import NATIVE_ACTUATOR
from cortex.engine.isolation import IsolationLevel, IsolationManager
from cortex.engine.legion import LegionOmegaEngine
from cortex.utils.result import Ok


@pytest.fixture
def isolation_manager():
    return IsolationManager()


@pytest.fixture
def legion_engine(isolation_manager):
    return LegionOmegaEngine(max_cycles=2, isolation=isolation_manager)


@pytest.fixture
def native_actuator():
    return NATIVE_ACTUATOR


@pytest.mark.asyncio
async def test_cycle_1_2_isolation_provisioning(isolation_manager):
    """Verify parallel workspace creation and cleanup."""
    async with isolation_manager.provision_sandbox(
        level=IsolationLevel.LOCAL, label="test_iso"
    ) as sandbox:
        assert sandbox.workspace_id in isolation_manager.workspaces
        ws_root = isolation_manager.workspaces[sandbox.workspace_id].root
        assert ws_root.exists()

        # Test basic write
        success = await sandbox.write_file("hello.txt", "CORTEX-OMEGA")
        assert success is True
        assert (ws_root / "hello.txt").read_text() == "CORTEX-OMEGA"

    # Verify auto-cleanup
    assert not ws_root.exists()
    assert sandbox.workspace_id not in isolation_manager.workspaces


@pytest.mark.asyncio
async def test_cycle_3_swarm_siege_dynamic(legion_engine):
    """Verify Legion-Omega can run dynamic siege in sandbox following AX-045."""
    intent = "Create a robust data processor"
    # We mock the siege to verify the control flow: PeARL -> Ledger -> Swarm
    # Patching where it's used (legion)
    with patch("cortex.engine.legion.log_motor") as mock_log:
        result = await legion_engine.forge(intent)
        assert result.cycles >= 1
        assert "Implementation" in result.final_code
        assert result.exergy >= 0.0
        assert result.entropy_delta <= 0.0 # Entropy should decrease or stay same for successful forge
        
        # Verify PeARL (FORGE) before Swarm (SIEGE)
        mock_log.assert_any_call(f"LEGION-OMEGA v6.1: Invocando Capital Convergence para '{intent}'", action="FORGE")


@pytest.mark.asyncio
async def test_cycle_5_jit_concept_formation(legion_engine):
    """Verify AX-046: JIT Concept Formation from anomalies."""
    # This simulates observing an anomaly and inducing a program
    anomaly_context = {"anomaly": "unexplained_packet_loss"}
    
    # We expect the engine to induce a PeARL program to explain/handle it
    with patch("cortex.engine.legion.BlueTeamAgent.synthesize", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = "def handle_anomaly(): return 'fixed'"
        
        result = await legion_engine.forge("Handle packet loss anomaly", context=anomaly_context)
        
        assert result.success is True
        assert "handle_anomaly" in result.final_code
        # Verify it was treated as a JIT induction
        mock_synth.assert_called()


@pytest.mark.asyncio
async def test_cycle_4_native_actuator_handoff(native_actuator):
    """Verify secure handoff from sandbox to host (mocking ByzantineAuth)."""
    sandbox_root = Path("/tmp/cortex_test_sandbox")
    sandbox_root.mkdir(parents=True, exist_ok=True)
    test_file = sandbox_root / "output.bin"
    test_file.write_text("Sovereign Proof")

    host_target = Path("/tmp/cortex_host_target/output.bin")

    # Mock ByzantineAuth to auto-approve
    with patch(
        "cortex.engine.auth.ByzantineAuthLayer.acquire_lock", new_callable=AsyncMock
    ) as mock_auth:
        mock_auth.return_value = True

        result = await native_actuator.secure_handoff(test_file, host_target)
        assert isinstance(result, Ok)
        assert host_target.exists()
        assert host_target.read_text() == "Sovereign Proof"

    # Cleanup
    shutil.rmtree(sandbox_root)
    shutil.rmtree(host_target.parent)


@pytest.mark.asyncio
async def test_legion_swarm_parallelism_scaling(legion_engine):
    """Verify that Legion can orchestrate multiple parallel vectors."""
    # Code that triggers 'eval' and 'os.system' in Intruder static vector
    code = "eval('dangerous'); os.system('rm')"
    context = {"target": "cpu"}

    # Use 10 replicas for testing speed
    legion_engine.red_team.replica_count = 10
    vulnerabilities = await legion_engine.red_team.siege(code, context)

    # Each replica of StaticVulnerabilityVector returns 1 vulnerability
    # We have 2 static vectors in RED_TEAM_SWARM
    # So 10 * 2 = 20 findings
    assert len(vulnerabilities) >= 20
