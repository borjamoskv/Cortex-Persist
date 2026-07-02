# [C5-REAL] Exergy-Maximized

import asyncio
import time
import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from babylon60.memory.manager import CortexMemoryManager
from babylon60.memory.engrams import CortexSemanticEngram
from babylon60.memory.models import MemoryEvent, SourceMetadata


@pytest.fixture
def mock_l1():
    l1 = MagicMock()
    l1.add_event = MagicMock(return_value=[])
    l1.get_context = MagicMock(return_value=[])
    return l1


@pytest.fixture
def mock_l2():
    l2 = MagicMock()
    l2._get_conn = MagicMock()
    l2.upsert = AsyncMock()
    l2.search_similar = AsyncMock(return_value=[])
    return l2


@pytest.fixture
def mock_l3():
    l3 = AsyncMock()
    l3.append_event = AsyncMock()
    return l3


@pytest.fixture
def mock_encoder():
    encoder = AsyncMock()
    encoder.encode = AsyncMock(return_value=[0.1] * 384)
    return encoder


@pytest_asyncio.fixture
async def manager(mock_l1, mock_l2, mock_l3, mock_encoder):
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        max_bg_tasks=1,
    )
    yield mgr
    await mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_manager_tenant_isolation(manager, mock_l1, mock_l3):
    """Verify tenant isolation in memory operations."""
    # Process interaction with tenant A
    await manager.process_interaction(
        role="user", content="Hello A", session_id="sess_a", token_count=10, tenant_id="tenant_a"
    )

    # Process interaction with tenant B
    await manager.process_interaction(
        role="user", content="Hello B", session_id="sess_b", token_count=10, tenant_id="tenant_b"
    )

    assert mock_l3.append_event.call_count == 2
    events = [call[0][0] for call in mock_l3.append_event.call_args_list]
    assert events[0].tenant_id == "tenant_a"
    assert events[1].tenant_id == "tenant_b"


@pytest.mark.asyncio
async def test_store_pipeline_states(manager, mock_encoder):
    """Test the states of the store pipeline (Mem0 -> Thalamus -> Resonance)."""
    # 1. Setup mocks for a successful store
    manager._mem0_pipeline = AsyncMock()
    manager._mem0_pipeline.evaluate_exergy = AsyncMock(return_value=MagicMock(score=0.9))
    manager._mem0_pipeline.exergy_threshold = 0.5

    manager.thalamus.filter = AsyncMock(return_value=(True, "encode:new", None))

    candidate_engram = CortexSemanticEngram(
        id="engram_1",
        tenant_id="t1",
        project_id="p1",
        content="content",
        embedding=[0.1] * 384,
        confidence="C5",
        source_metadata=SourceMetadata(origin="system", author="test", confidence_in_source=1.0),
    )
    manager._resonance_gate.gate = AsyncMock(return_value=("reset", candidate_engram))

    with patch("cortex.memory.manager.CortexMemoryManager._check_deduplication", return_value=None):
        fact_id = await manager.store(
            tenant_id="t1",
            project_id="p1",
            content="Validated content",
            fact_type="knowledge",
            metadata={
                "confidence_score": "C5",
                "source_metadata": {
                    "origin": "system",
                    "author": "test",
                    "confidence_in_source": 1.0,
                },
            },
        )

    assert fact_id == "engram_1"
    manager._mem0_pipeline.evaluate_exergy.assert_called_once()
    manager.thalamus.filter.assert_called_once()
    manager._resonance_gate.gate.assert_called_once()


@pytest.mark.asyncio
async def test_store_rollback_resonance_failure(manager):
    """Test behavior when resonance gate fails (simulating rollback/abort)."""
    manager._mem0_pipeline = AsyncMock()
    manager._mem0_pipeline.evaluate_exergy = AsyncMock(return_value=MagicMock(score=0.9))
    manager._mem0_pipeline.exergy_threshold = 0.5
    manager.thalamus.filter = AsyncMock(return_value=(True, "encode:new", None))

    # Simulate a failure in resonance gate (e.g. database error)
    manager._resonance_gate.gate = AsyncMock(side_effect=RuntimeError("Resonance failure"))

    with patch("cortex.memory.manager.CortexMemoryManager._check_deduplication", return_value=None):
        with pytest.raises(RuntimeError, match="Resonance failure"):
            await manager.store(
                tenant_id="t1",
                content="This will fail",
                metadata={
                    "confidence_score": "C5",
                    "source_metadata": {
                        "origin": "system",
                        "author": "test",
                        "confidence_in_source": 1.0,
                    },
                },
            )


@pytest.mark.asyncio
async def test_assemble_context_isolation(manager, mock_l1):
    """Verify tenant isolation in context assembly."""
    with patch(
        "babylon60.memory.memory_retrieval.retrieve_episodic_context", new_callable=AsyncMock
    ) as mock_retrieve:
        mock_retrieve.return_value = []

        await manager.assemble_context(tenant_id="tenant_a", query="hi")
        mock_l1.get_context.assert_called_with(tenant_id="tenant_a")

        await manager.assemble_context(tenant_id="tenant_b", query="hi")
        mock_l1.get_context.assert_called_with(tenant_id="tenant_b")


@pytest.mark.asyncio
async def test_deduplication_exact_match(manager, mock_l2):
    """Test the deduplication check in store()."""
    # Setup mock L2 connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_l2._get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {"id": "existing_id"}

    manager._mem0_pipeline = AsyncMock()
    manager._mem0_pipeline.evaluate_exergy = AsyncMock(return_value=MagicMock(score=0.9))
    manager._mem0_pipeline.exergy_threshold = 0.5
    manager.thalamus.filter = AsyncMock(return_value=(True, "encode:new", None))

    with patch(
        "cortex.memory.manager.CortexMemoryManager._check_deduplication",
        side_effect=manager._check_deduplication,
    ):
        fact_id = await manager.store(tenant_id="t1", project_id="p1", content="Already exists")

    assert fact_id == "deduplicated:existing_id"
    # Verify it didn't proceed to encoding or resonance
    assert manager._encoder.encode.call_count == 0


@pytest.mark.asyncio
async def test_wait_for_background_success(manager):
    """Test wait_for_background with actual task completion."""
    # Mock compress_and_store to do nothing
    with patch("cortex.memory._manager_bg.compress_and_store", new_callable=AsyncMock):
        manager._bg_queue.put_nowait((["item"], "s", "t", "p"))
        # The worker should pick it up and call task_done
        await manager.wait_for_background(timeout=1.0)
        assert manager._bg_queue.empty()
