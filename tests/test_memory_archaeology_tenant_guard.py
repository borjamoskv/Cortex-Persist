from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cortex.memory.memory_archaeology import MemoryArchaeologist


class _DummySession:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeEngine:
    def __init__(self) -> None:
        self.store = AsyncMock(return_value=999)

    def session(self) -> _DummySession:
        return _DummySession()


@pytest.mark.asyncio
async def test_apply_db_updates_rejects_cross_tenant_cluster_before_store() -> None:
    archaeologist = MemoryArchaeologist(_FakeEngine())

    with pytest.raises(ValueError, match="multiple tenants"):
        await archaeologist._apply_db_updates(
            "alpha",
            "tenant-a",
            "merged fact",
            [
                {"id": "1", "tenant_id": "tenant-a", "content": "a", "parent_decision_id": None},
                {"id": "2", "tenant_id": "tenant-b", "content": "b", "parent_decision_id": None},
            ],
            None,
            object(),  # type: ignore[arg-type]
        )

    archaeologist.engine.store.assert_not_awaited()
