import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from cortex.memory.memory_archaeology import MemoryArchaeologist

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.memory._l2._get_conn.return_value = MagicMock()
    return engine

def test_build_clusters_vectorized(mock_engine):
    archaeology = MemoryArchaeologist(mock_engine)

    # 3 facts, first 2 are similar
    facts = [
        {"id": 1, "content": "fact 1"},
        {"id": 2, "content": "fact 1 similar"},
        {"id": 3, "content": "fact 3 different"}
    ]

    # Normalized vectors
    v1 = np.array([1.0, 0.0])
    v2 = np.array([0.9, 0.1])
    v2 = v2 / np.linalg.norm(v2)
    v3 = np.array([0.0, 1.0])

    vecs_matrix = np.vstack([v1, v2, v3])

    clusters = archaeology._build_clusters(facts, vecs_matrix, threshold=0.8)

    # Should cluster fact 0 and 1 together
    assert len(clusters) == 1
    assert 0 in clusters[0]
    assert 1 in clusters[0]
    assert 2 not in clusters[0]

@pytest.mark.asyncio
async def test_synthesize_and_update_concurrency(mock_engine):
    archaeology = MemoryArchaeologist(mock_engine)

    # Mock LLM
    archaeology.llm = AsyncMock()
    mock_res = MagicMock()
    mock_res.text = "Condensed Fact"
    archaeology.llm.agenerate.return_value = mock_res

    archaeology._apply_db_updates = AsyncMock()

    facts = [
        {"id": "1", "content": "A", "parent_decision_id": None},
        {"id": "2", "content": "B", "parent_decision_id": None},
        {"id": "3", "content": "C", "parent_decision_id": None},
        {"id": "4", "content": "D", "parent_decision_id": None},
    ]

    clusters = [[0, 1], [2, 3]]

    condensed, tombstoned = await archaeology._synthesize_and_update(
        "test_project", "tenant_1", clusters, facts, simulate=False
    )

    assert condensed == 2
    assert tombstoned == 4

    assert archaeology.llm.agenerate.call_count == 2
    assert archaeology._apply_db_updates.call_count == 2

@pytest.mark.asyncio
async def test_synthesize_missing_llm(mock_engine):
    archaeology = MemoryArchaeologist(mock_engine)
    archaeology.llm = None

    condensed, tombstoned = await archaeology._synthesize_and_update(
        "test_project", "tenant_1", [[0, 1]], [{"id": 1, "content": "A", "parent_decision_id": None}, {"id": 2, "content": "B", "parent_decision_id": None}], simulate=False
    )
    assert condensed == 0
    assert tombstoned == 0

@pytest.mark.asyncio
async def test_synthesize_overlapping_locks(mock_engine):
    archaeology = MemoryArchaeologist(mock_engine)

    # Mock LLM
    archaeology.llm = AsyncMock()
    mock_res = MagicMock()
    mock_res.text = "Condensed Fact"
    archaeology.llm.agenerate.return_value = mock_res

    archaeology._apply_db_updates = AsyncMock()

    facts = [
        {"id": "1", "content": "A", "parent_decision_id": None},
        {"id": "2", "content": "B", "parent_decision_id": None},
        {"id": "3", "content": "C", "parent_decision_id": None},
    ]

    # Overlapping clusters
    clusters = [[0, 1], [1, 2]]

    condensed, tombstoned = await archaeology._synthesize_and_update(
        "test_project", "tenant_1", clusters, facts, simulate=False
    )

    assert condensed == 1
    assert tombstoned == 2

    assert archaeology.llm.agenerate.call_count == 1
    assert archaeology._apply_db_updates.call_count == 1

@pytest.mark.asyncio
async def test_synthesize_db_error(mock_engine):
    import sqlite3
    archaeology = MemoryArchaeologist(mock_engine)

    # Mock LLM
    archaeology.llm = AsyncMock()
    mock_res = MagicMock()
    mock_res.text = "Condensed Fact"
    archaeology.llm.agenerate.return_value = mock_res

    archaeology._apply_db_updates = AsyncMock(side_effect=sqlite3.Error("Mock error"))

    facts = [
        {"id": "1", "content": "A", "parent_decision_id": None},
        {"id": "2", "content": "B", "parent_decision_id": None},
    ]

    clusters = [[0, 1]]

    condensed, tombstoned = await archaeology._synthesize_and_update(
        "test_project", "tenant_1", clusters, facts, simulate=False
    )

    assert condensed == 0
    assert tombstoned == 0
