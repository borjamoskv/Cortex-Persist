import pytest
import asyncio
import numpy as np
from cortex.core.lineage import LineageVerifier
from cortex.memory.memory_archaeology import MemoryArchaeologist
from dataclasses import dataclass
from typing import Any


@dataclass
class DummyFact:
    id: int
    project: str
    content: str
    fact_type: str
    confidence: str
    created_at: str
    tx_id: str | None
    meta: dict[str, Any]


class DummyEngine:
    def __init__(self):
        self.facts = {
            1: DummyFact(
                1,
                "test",
                "Fact 1",
                "knowledge",
                "high",
                "2023-01-01",
                "tx1",
                {"lineage_sources": []},
            ),
            2: DummyFact(
                2,
                "test",
                "Fact 2",
                "knowledge",
                "high",
                "2023-01-02",
                "tx2",
                {"lineage_sources": [1]},
            ),
            3: DummyFact(
                3,
                "test",
                "Fact 3",
                "knowledge",
                "high",
                "2023-01-03",
                "tx3",
                {"lineage_sources": [2]},
            ),
            4: DummyFact(
                4,
                "test",
                "Fact 4",
                "knowledge",
                "high",
                "2023-01-04",
                "tx4",
                {"lineage_sources": [4]},
            ),  # Cycle!
        }

    async def get_fact(self, fact_id: int):
        # Simulate network/db delay to trigger concurrency issues if they exist
        await asyncio.sleep(0.01)
        return self.facts.get(fact_id)


@pytest.mark.asyncio
async def test_lineage_verifier_concurrency():
    engine = DummyEngine()
    verifier = LineageVerifier(engine)

    # Normal fetch
    node = await verifier.get_lineage(3)
    assert node.fact_id == 3  # nosec B101
    assert len(node.parents) == 1  # nosec B101
    assert node.parents[0].fact_id == 2  # nosec B101
    assert len(node.parents[0].parents) == 1  # nosec B101
    assert node.parents[0].parents[0].fact_id == 1  # nosec B101
    assert len(node.parents[0].parents[0].parents) == 0  # nosec B101


@pytest.mark.asyncio
async def test_lineage_verifier_cycle():
    engine = DummyEngine()
    verifier = LineageVerifier(engine)

    # Cycle fetch
    node = await verifier.get_lineage(4)
    assert node.fact_id == 4  # nosec B101
    assert len(node.parents) == 1  # nosec B101
    assert node.parents[0].fact_id == 4  # nosec B101
    assert node.parents[0].error == "Cyclic graph lineage protection triggered."  # nosec B101


def test_archaeologist_build_clusters():
    archaeologist = MemoryArchaeologist(engine=None)

    # 4 facts
    facts = [{"id": i} for i in range(4)]

    # 2 clusters: (0, 1) and (2, 3)
    vecs_matrix = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],
        ]
    )

    clusters = archaeologist._build_clusters(facts, vecs_matrix, threshold=0.9)
    assert len(clusters) == 2  # nosec B101

    # Note: the exact structure depends on ordering, but we expect sizes to be 2 and 2
    assert set(clusters[0]) == {0, 1}  # nosec B101
    assert set(clusters[1]) == {2, 3}  # nosec B101


def test_archaeologist_no_clusters():
    archaeologist = MemoryArchaeologist(engine=None)

    facts = [{"id": i} for i in range(3)]

    # All orthogonal
    vecs_matrix = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    clusters = archaeologist._build_clusters(facts, vecs_matrix, threshold=0.9)
    assert len(clusters) == 0  # nosec B101
