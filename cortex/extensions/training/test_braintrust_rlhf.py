import asyncio
import datetime
import uuid

from cortex.extensions.aether.sovereign_apis import SovereignTriad
from cortex.extensions.episodic.base import Episode
from cortex.extensions.training.collector import TrajectoryCollector
from cortex.extensions.training.reward_engine import RewardEngine


class MockEpisodicMemory:
    """Mock for episodic memory to simulate session extraction."""

    async def get_session_timeline(self, session_id: str) -> list[Episode]:
        # Simulamos una trayectoria simple de éxito.
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        def ep(evt, content, intent="", meta=None):
            return Episode(
                id=int(uuid.uuid4().hex[:8], 16),
                session_id=session_id,
                project="test_rlhf",
                event_type=evt,
                content=content,
                intent=intent,
                meta=meta or {},
                emotion="neutral",
                tags=[],
                created_at=now,
            )

        return [
            ep(
                "decision",
                "Instrucción de prueba Braintrust",
                intent="Fix the bug locally",
                meta={"tool": "search", "input": {"q": "bug"}},
            ),
            ep("discovery", "Found bug on line 42"),
            ep(
                "decision",
                "Decide fix",
                meta={
                    "tool": "write",
                    "input": {"file": "bug.py"},
                    "lines_added": 10,
                    "lines_deleted": 20,
                    "tests_passed": True,
                },
            ),
            ep("milestone", "Task success", meta={"avg_confidence": 0.95}),
        ]


async def run_triad_rlhf_sandbox():
    print("[SOVEREIGN SANDBOX] Iniciando Pruebas RLHF con Braintrust...")

    mock_memory = MockEpisodicMemory()
    _triad = SovereignTriad()

    # Force mock API KEY if not present for log tracking attempt without hard failing.
    # _triad.braintrust_key = "fake_key_para_evitar_warnings"

    session_id = f"sandbox_{uuid.uuid4().hex[:8]}"

    collector = TrajectoryCollector(episodic_memory=mock_memory)
    engine = RewardEngine(use_tests=True)

    print(f"1. Extrayendo trayectoria virtual (ID: {session_id})")
    trajectory = await collector.collect_session_trajectory(session_id)

    if not trajectory:
        print("Fallo recolectando trayectoria.")
        return

    print("2. Trayectoria Extraída:")
    print(f"   - Proyecto: {trajectory.project}")
    print(f"   - Acciones: {len(trajectory.actions)}")
    print(f"   - Outcome Inferido: {trajectory.outcome}")

    print("3. Calculando Sovereign V2 Reward (Sincronizado a Braintrust)")
    reward = engine.calculate_reward(trajectory)

    print(f"   => SCORE FINAL (Escala [-1.0, 1.0]): {reward:.3f}")
    print("4. Braintrust trace execution triggers in background via SovereignTriad O(1).")


if __name__ == "__main__":
    asyncio.run(run_triad_rlhf_sandbox())
