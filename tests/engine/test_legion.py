# [C5-REAL] Exergy-Maximized
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Any
from cortex.engine.swarm.legion import (
    SwarmSignal,
    AsyncSignalBus,
    SwarmAgent,
    Squadron,
    BlueTeamAgent,
    RedTeamSwarm,
    LegionOmegaEngine,
    SiegeResult,
)


class MockAgent(SwarmAgent):
    async def execute(self, target: str) -> SwarmSignal:
        if target == "fail":
            raise ValueError("Injected failure")
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={
                "msg": f"Processed {target}",
                "proof": "Proof: { Base: 'Test', Range: [0,1], Confidence: C5-REAL }",
            },
            metrics={"time": 0.1},
        )


class MockSquadron(Squadron):
    SQUAD_NAME = "TEST"
    REPLICAS = 2

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        return MockAgent(agent_id, self.bus, self.engine)


@pytest.mark.asyncio
async def test_async_signal_bus():
    """Validates AsyncSignalBus emission and VOID status enforcement."""
    bus = AsyncSignalBus()

    # Normal signal
    sig1 = SwarmSignal("a1", "t1", "SUCCESS", {"key": "val"}, {})
    await bus.emit(sig1)

    # Empty payload with SUCCESS -> Raises ValueError (P0 Violation)
    sig2 = SwarmSignal("a2", "t2", "SUCCESS", {}, {})
    with pytest.raises(ValueError, match="SUCCESS signal emitted with empty payload"):
        await bus.emit(sig2)

    # Empty payload with other status -> Converted to VOID
    sig3 = SwarmSignal("a3", "t3", "UNKNOWN", {}, {})
    await bus.emit(sig3)

    signals = await bus.get_all()
    assert len(signals) == 2
    assert signals[0].status == "SUCCESS"
    assert signals[1].status == "VOID"


@pytest.mark.asyncio
async def test_swarm_agent_run():
    """Validates SwarmAgent execution loop and error handling."""
    bus = AsyncSignalBus()
    agent = MockAgent("agent-001", bus)
    queue = asyncio.Queue()

    await queue.put("task1")
    await queue.put("fail")
    await queue.put(None)

    # Run agent until queue is empty
    await agent.run(queue)

    signals = await bus.get_all()
    assert len(signals) == 2
    assert signals[0].target == "task1"
    assert signals[0].status == "SUCCESS"
    assert signals[1].target == "fail"
    assert signals[1].status == "FAILURE"
    assert "Injected failure" in signals[1].payload["error"]


@pytest.mark.asyncio
async def test_squadron_deploy():
    """Validates Squadron orchestration of multiple agents."""
    squad = MockSquadron()
    report = await squad.deploy("target-pattern")

    assert report["squadron"] == "TEST"
    assert report["total_signals"] == 1
    assert report["success"] == 1
    assert len(squad.agents) == 2


@pytest.mark.asyncio
async def test_blue_team_agent_synthesis():
    """Validates BlueTeamAgent code synthesis based on intent and feedback."""
    blue = BlueTeamAgent()

    # Initial synthesis
    code = await blue.synthesize("test eval", {})
    assert "eval" in code
    assert "def run_dynamic" in code

    # Feedback-driven synthesis
    feedback = ["Contains eval", "Has bare except"]
    code2 = await blue.synthesize("test", {}, feedback)
    assert "import ast" in code2
    assert "ast.literal_eval" in code2
    assert "except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:" in code2


@pytest.mark.asyncio
async def test_red_team_swarm_siege():
    """Validates RedTeamSwarm siege execution with mock vectors."""
    mock_vector = MagicMock()
    mock_vector.attack = AsyncMock(return_value=["vulnerability found"])

    swarm = RedTeamSwarm(vectors=[mock_vector], replica_count=2)
    findings = await swarm.siege("some code", {})

    assert len(findings) == 2
    assert findings[0] == "vulnerability found"
    assert mock_vector.attack.call_count == 2


@pytest.mark.asyncio
async def test_legion_omega_engine_forge_success():
    """Validates LegionOmegaEngine forge cycle leading to immunity."""
    # Mock Blue team to return specific code
    # Mock Red team to return no vulnerabilities on second cycle
    engine = LegionOmegaEngine(max_cycles=3)
    engine.red_team = MagicMock()

    # Provide different code for each cycle to avoid thermal stagnation
    engine.blue_team.synthesize = AsyncMock(side_effect=["code1", "code2", "code3"])

    # Cycle 1: vulnerabilities found
    # Cycle 2: no vulnerabilities
    engine.red_team.siege = AsyncMock(side_effect=[["bug"], []])

    result = await engine.forge("secure task")
    assert result.success is True
    assert result.cycles == 2
    assert len(result.vulnerabilities) == 0


@pytest.mark.asyncio
async def test_legion_omega_engine_forge_failure():
    """Validates LegionOmegaEngine forge cycle exhaustion."""
    engine = LegionOmegaEngine(max_cycles=2)
    engine.red_team = MagicMock()
    engine.red_team.siege = AsyncMock(return_value=["persistent bug"])

    result = await engine.forge("hard task")
    assert result.success is False
    assert result.cycles == 2
    assert "persistent bug" in result.vulnerabilities


@pytest.mark.asyncio
async def test_legion_omega_engine_thermal_stagnation():
    """Validates thermal stagnation guard in LegionOmegaEngine."""
    engine = LegionOmegaEngine(max_cycles=5)

    # Mock blue team to return SAME code twice
    engine.blue_team.synthesize = AsyncMock(return_value="stable code")
    engine.red_team.siege = AsyncMock(return_value=["bug"])

    result = await engine.forge("stable task")
    # Should break early due to code identity
    assert result.cycles < 5


@pytest.mark.asyncio
async def test_squadron_crystallize_cross_system_invariance():
    """Validates that Squadron crystallization runs Cross-System verifier when context exists."""
    from cortex.shannon.env.trace import EpisodeTrace, StepTrace
    from cortex.engine.core.evolution_ledger import ControlVector, MutationRecord

    # 1. Create a matching Shannon trace
    steps = [
        StepTrace(
            step_idx=0,
            observation_hex="010203",
            action_hex="aabbcc",
            reward=1.0,
            done=False,
            info={},
            timestamp=1718000000.0,
        ),
    ]
    from cortex.shannon.env.trace import compute_trace_checksum

    checksum = compute_trace_checksum("genesis-v1", "000000", steps)
    trace = EpisodeTrace(
        env_id="genesis-v1",
        env_kwargs={"seed": 42},
        seed=42,
        initial_observation_hex="000000",
        steps=steps,
        checksum=checksum,
    )

    # 2. Create matching substrate records
    records = [
        MutationRecord(
            sequence=1,
            agent_idx=0,
            timestamp=1718000000.0,
            prev_hash="GENESIS",
            hash="h1",
            vector_before=None,
            vector_after=ControlVector(10.0, 0.05, 0.1, 0.6),
            performance_delta=100.0,
            source="substrate",
        )
    ]

    # 3. Custom engine wrapper to provide trace and records
    class MockEngine:
        def __init__(self):
            self.shannon_trace = trace
            self.substrate_ledger = records

    engine = MockEngine()

    # 4. Mock squadron with agents emitting correct matching signals
    class CustomMockAgent(SwarmAgent):
        async def execute(self, target: str) -> SwarmSignal:
            return SwarmSignal(
                agent_id=self.agent_id,
                target=target,
                status="SUCCESS",
                payload={
                    "action_hex": "aabbcc",
                    "observation_hex": "010203",
                    "reward": 1.0,
                    "done": False,
                    "proof": "Proof: { Base: 'Test', Range: [0,1], Confidence: C5-REAL }",
                },
                metrics={},
            )

    class CustomMockSquadron(Squadron):
        SQUAD_NAME = "INVARIANT_TEST"
        REPLICAS = 1

        def _create_agent(self, agent_id: str) -> SwarmAgent:
            return CustomMockAgent(agent_id, self.bus, self.engine)

    squad = CustomMockSquadron(engine=engine)

    # 5. Deploy and verify it passes
    report = await squad.deploy("target-1")
    assert report["squadron"] == "INVARIANT_TEST"
    assert report["total_signals"] == 1

    # 6. Test with a mismatched trace (e.g. empty trace) to verify it raises and fails
    engine.shannon_trace = EpisodeTrace(
        env_id="mismatch-v1",
        env_kwargs={"seed": 99},
        seed=99,
        initial_observation_hex="000000",
        steps=[],
        checksum="bad",
    )

    with pytest.raises(RuntimeError, match="Cross-System Invariance Violation"):
        await squad.deploy("target-2")
