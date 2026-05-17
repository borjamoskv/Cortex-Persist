import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass, field

from cortex.memory.sleep import SleepOrchestrator
from cortex.memory.dream import AssociativeDreamEngine
from cortex.memory.replay import HippocampalReplay
from cortex.memory.metamemory import MetamemoryMonitor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cortex.test")


@dataclass
class MockEngram:
    id: str
    content: str = "Test content"
    embedding: list[float] = field(default_factory=lambda: [0.0] * 384)
    project_id: str = "test_project"
    tenant_id: str = "test_tenant"
    success_rate: float = 0.8
    energy_level: float = 0.6
    exergy_score: float = 0.0
    entangled_refs: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    is_diamond: bool = False
    is_bridge: bool = False
    is_synthetic: bool = False
    access_count: int = 1
    confidence: str = "C5"
    causal_weight: float = 0.0


async def simulate_sleep_cycle():
    logger.info("Starting C5-REAL Sleep Cycle Simulation...")

    # 1. Setup Mocks
    mock_vs = AsyncMock()

    # Create some mock engrams
    engrams = [
        MockEngram(
            "e1",
            "Fact 1",
            [1.0, 0.0],
            success_rate=0.9,
            energy_level=0.8,
            entangled_refs=["e2", "e3"],
        ),
        MockEngram(
            "e2", "Fact 2", [1.0, 0.05], success_rate=0.7, energy_level=0.5, entangled_refs=["e1"]
        ),
        MockEngram(
            "e3", "Fact 3", [0.95, 0.1], success_rate=0.4, energy_level=0.3, entangled_refs=["e1"]
        ),
        MockEngram("e4", "Fact 4 (Isolated)", [0.0, 1.0], energy_level=0.1, access_count=20),
        MockEngram("e5", "Diamond Fact", [0.5, 0.5], is_diamond=True),
        MockEngram("e6", "Zombie Fact", [0.1, 0.1], energy_level=0.0001, access_count=100),
    ]

    mock_vs.scan_engrams.return_value = engrams
    mock_vs.upsert_batch = AsyncMock()
    mock_vs.delete = AsyncMock(return_value=True)

    mock_replay = MagicMock(spec=HippocampalReplay)
    mock_replay.replay_cycle = AsyncMock(
        return_value=MagicMock(merged=1, reinforced=2, conflicts=0, pruned=0, duration_ms=15.0)
    )

    mock_metamemory = MagicMock(spec=MetamemoryMonitor)
    mock_metamemory.calibration_score.return_value = 0.12
    mock_metamemory._fok_threshold = 0.3
    mock_metamemory.calibration_report.return_value = {
        "segmented_brier": {"math": 0.08, "coding": 0.15}
    }
    mock_metamemory.knowledge_gaps.return_value = []

    # Inject mock_vs into nrem to simulate sleep.py's _run_thermodynamic_pruning
    mock_replay._vs = mock_vs

    # AssociativeDreamEngine
    dream_engine = AssociativeDreamEngine(vector_store=mock_vs, metamemory=mock_metamemory)

    orchestrator = SleepOrchestrator(nrem=mock_replay, rem=dream_engine, metamemory=mock_metamemory)

    # 2. Run Cycle
    logger.info("Executing run_full_cycle('test_tenant')...")
    report = await orchestrator.run_full_cycle("test_tenant", hot_engrams=None)

    # 3. Verify Results
    logger.info("-" * 40)
    logger.info("Report Summary:")
    logger.info(f"  NREM: Merged={report.nrem_merged}, Reinforced={report.nrem_reinforced}")
    logger.info(
        f"  REM: Clusters={report.rem_clusters_found}, Bridges={report.rem_bridges_created}, Reweighted={report.rem_engrams_reweighted}"
    )
    logger.info(
        f"  Thermodynamic Pruning: Pruned={report.thermodynamic_pruned}, Released Entropy={report.released_entropy:.4f}"
    )
    logger.info(f"  Calibration: Brier={report.brier_before:.4f} -> {report.brier_after:.4f}")
    logger.info("-" * 40)

    # Check if exergies were calculated and persisted
    if mock_vs.upsert_batch.called:
        logger.info("SUCCESS: upsert_batch was called for exergy persistence.")
        # Check first batch call (usually from sleep.py or dream.py)
        # We expect at least one call from sleep.py and one from dream.py
        logger.info(f"  upsert_batch call count: {mock_vs.upsert_batch.call_count}")
    else:
        logger.error("FAILURE: upsert_batch was NOT called.")

    # Check if isolated node was pruned
    if mock_vs.delete.called:
        logger.info(
            f"SUCCESS: delete was called {mock_vs.delete.call_count} times for thermodynamic pruning."
        )
    else:
        logger.info("Note: No nodes were pruned (depends on threshold).")


if __name__ == "__main__":
    asyncio.run(simulate_sleep_cycle())
