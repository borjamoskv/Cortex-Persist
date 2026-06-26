# [C5-REAL] Exergy-Maximized
"""
Tests for CortexMemoryManager - Edge cases and isolated boundaries.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from cortex.memory.manager import CortexMemoryManager
from cortex.memory.models import MemoryEvent


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
async def test_process_interaction_success(manager, mock_l1, mock_l3):
    """Test standard interaction completes successfully."""
    event = await manager.process_interaction(
        role="user",
        content="Hello world",
        session_id="session_1",
        token_count=10,
        tenant_id="tenant_x",
    )
    assert event.role == "user"
    assert event.content == "Hello world"
    mock_l3.append_event.assert_called_once()
    mock_l1.add_event.assert_called_once()


@pytest.mark.asyncio
async def test_background_tasks_cancellation(manager):
    """Verify background tasks can be cancelled without throwing."""
    # Register a worker task
    task = asyncio.create_task(asyncio.sleep(10))
    manager._bg_workers.append(task)
    
    # Trigger cancellation
    await manager._cancel_background_tasks()
    
    # All tasks should be cancelled or completed
    assert all(t.cancelled() or t.done() for t in manager._bg_workers)


@pytest.mark.asyncio
async def test_wait_for_background_timeout(manager):
    """Verify wait_for_background handles timeouts gracefully."""
    # Stop background workers first to prevent queue consumption
    for worker in manager._bg_workers:
        worker.cancel()
    manager._bg_workers.clear()
    
    # Enqueue a mock item into the queue
    await manager._bg_queue.put(([], "sess", "tenant", "proj"))
    
    with patch("cortex.memory.manager.logger") as mock_logger:
        await manager.wait_for_background(timeout=0.01)
        # Should have logged error due to timeout
        mock_logger.error.assert_called()
