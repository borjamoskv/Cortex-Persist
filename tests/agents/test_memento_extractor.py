"""Tests for the LlmSessionExtractor (MEMENTO component)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.agents.builtins.memento_extractor import LlmSessionExtractor
from cortex.extensions.llm.router import CortexLLMRouter
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.models import MemoryEvent


@pytest.fixture
def mock_l3() -> AsyncMock:
    l3 = AsyncMock()
    # Mock the internal connection
    l3._conn = AsyncMock()
    return l3


@pytest.fixture
def mock_manager(mock_l3) -> MagicMock:
    manager = MagicMock(spec=CortexMemoryManager)
    manager.l3.return_value = mock_l3
    return manager


@pytest.fixture
def mock_router() -> MagicMock:
    router = MagicMock(spec=CortexLLMRouter)
    router.execute_resilient = AsyncMock()
    return router


@pytest.fixture
def extractor(mock_manager, mock_router) -> LlmSessionExtractor:
    return LlmSessionExtractor(
        manager=mock_manager,
        router=mock_router,
        idle_minutes=15,
    )


@pytest.mark.asyncio
async def test_pending_sessions(extractor: LlmSessionExtractor, mock_l3: AsyncMock) -> None:
    # Mock the cursor fetching
    cursor_mock = AsyncMock()
    cursor_mock.fetchall.return_value = [("session-1", "tenant-A"), ("session-2", "tenant-A")]
    mock_l3._conn.execute.return_value = cursor_mock

    sessions = await extractor.pending_sessions()

    assert len(sessions) == 2
    assert sessions[0]["session_id"] == "session-1"
    assert sessions[1]["session_id"] == "session-2"
    assert "project_id" in sessions[0]

    mock_l3._conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_extract_success(
    extractor: LlmSessionExtractor, mock_l3: AsyncMock, mock_router: MagicMock
) -> None:
    # Mock L3 events for a session
    mock_l3.get_session_events.return_value = [
        MemoryEvent(
            event_id="e1",
            timestamp=datetime.now(timezone.utc),
            role="user",
            content="Can we use PostgreSQL?",
            session_id="session-1",
            tenant_id="tenant-A",
            token_count=0,
            prev_hash="",
            signature="",
            metadata={},
        ),
        MemoryEvent(
            event_id="e2",
            timestamp=datetime.now(timezone.utc),
            role="assistant",
            content="Yes, we will use PostgreSQL.",
            session_id="session-1",
            tenant_id="tenant-A",
            token_count=0,
            prev_hash="",
            signature="",
            metadata={},
        ),
    ]

    # Mock the router response
    mock_result = MagicMock()
    mock_result.is_ok.return_value = True
    mock_result.unwrap.return_value = json.dumps(
        [
            {
                "content": "User selected PostgreSQL for the database.",
                "fact_type": "decision",
                "confidence": 0.9,
            }
        ]
    )
    mock_router.execute_resilient.return_value = mock_result

    insights = await extractor.extract({"session_id": "session-1", "tenant_id": "tenant-A"})

    assert len(insights) == 1
    assert insights[0]["content"] == "User selected PostgreSQL for the database."
    assert insights[0]["fact_type"] == "decision"
    assert insights[0]["confidence"] == 0.9

    mock_router.execute_resilient.assert_called_once()
    prompt = mock_router.execute_resilient.call_args[0][0]
    # Check that transcript is in the prompt
    assert "PostgreSQL" in prompt.working_memory[0]["content"]


@pytest.mark.asyncio
async def test_extract_empty_events(
    extractor: LlmSessionExtractor, mock_l3: AsyncMock, mock_router: MagicMock
) -> None:
    mock_l3.get_session_events.return_value = []

    insights = await extractor.extract({"session_id": "session-1"})

    assert insights == []
    mock_router.execute_resilient.assert_not_called()


@pytest.mark.asyncio
async def test_extract_invalid_json(
    extractor: LlmSessionExtractor, mock_l3: AsyncMock, mock_router: MagicMock
) -> None:
    mock_l3.get_session_events.return_value = [
        MemoryEvent(
            event_id="e1",
            timestamp=datetime.now(timezone.utc),
            role="user",
            content="hello",
            session_id="session-1",
            tenant_id="tenant-A",
            token_count=0,
            prev_hash="",
            signature="",
            metadata={},
        )
    ]

    mock_result = MagicMock()
    mock_result.is_ok.return_value = True
    mock_result.unwrap.return_value = "invalid json {["
    mock_router.execute_resilient.return_value = mock_result

    with pytest.raises(RuntimeError, match="JSON decode failed"):
        await extractor.extract({"session_id": "session-1"})


@pytest.mark.asyncio
async def test_mark_processed(extractor: LlmSessionExtractor, mock_l3: AsyncMock) -> None:
    await extractor.mark_processed("session-1")

    mock_l3.append_event.assert_called_once()
    event = mock_l3.append_event.call_args[0][0]

    assert event.session_id == "session-1"
    assert event.role == "system"
    assert event.content == "[MEMENTO] Crystallization complete"
