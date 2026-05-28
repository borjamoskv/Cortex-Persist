from dataclasses import dataclass, field

import pytest

from cortex.memory.dream import AssociativeDreamEngine, DreamResult


@dataclass
class MockEngram:
    id: str
    embedding: list[float]
    project_id: str = "test_project"
    entangled_refs: list[str] = field(default_factory=list)
    energy_level: float = 0.5
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0


@pytest.mark.asyncio
async def test_dream_cycle_basic():
    """Verify that AssociativeDreamEngine can cluster similar engrams."""
    # Group A: Similar vectors
    e1 = MockEngram("1", [1.0, 0.0, 0.0])
    e2 = MockEngram("2", [0.99, 0.01, 0.0])
    # Group B: Different vector
    e3 = MockEngram("3", [0.0, 1.0, 0.0])

    engine = AssociativeDreamEngine(cluster_threshold=0.9)
    result = await engine.dream_cycle(tenant_id="test", engrams=[e1, e2, e3])

    assert isinstance(result, DreamResult)
    assert result.clusters_found == 1  # e1 and e2 should cluster
    assert result.bridges_created == 0
    assert result.duration_ms >= 0
