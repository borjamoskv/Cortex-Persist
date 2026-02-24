from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.vector_store import VectorStoreL2
from cortex.memory.working import WorkingMemoryL1


@pytest.fixture
def mock_deps():
    l1 = MagicMock(spec=WorkingMemoryL1)
    l2 = AsyncMock(spec=VectorStoreL2)
    l3 = AsyncMock(spec=EventLedgerL3)
    encoder = AsyncMock(spec=AsyncEncoder)
    return l1, l2, l3, encoder


@pytest.mark.asyncio
async def test_tenant_isolation_in_ledger(mock_deps):
    l1, l2, l3, encoder = mock_deps
    manager = CortexMemoryManager(l1, l2, l3, encoder)

    # Simulating interaction for Tenant A
    await manager.process_interaction(
        role="user",
        content="Sensitive info for A",
        session_id="session-1",
        token_count=10,
        tenant_id="tenant-A",
    )

    # Verify L3 append received the tenant_id
    args, _ = l3.append_event.call_args
    event = args[0]
    assert event.tenant_id == "tenant-A"
    assert event.content == "Sensitive info for A"


@pytest.mark.asyncio
async def test_tenant_isolation_in_recall(mock_deps):
    l1, l2, l3, encoder = mock_deps
    manager = CortexMemoryManager(l1, l2, l3, encoder)

    # Scenario: User from Tenant B tries to recall memory
    await manager.assemble_context(query="some query", tenant_id="tenant-B", project_id="test-proj")

    # Verification complete.
    l2.recall.assert_called_once_with(query="some query", limit=3, tenant_id="tenant-B")
