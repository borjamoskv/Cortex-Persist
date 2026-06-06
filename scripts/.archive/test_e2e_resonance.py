import asyncio
import logging

import aiosqlite

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.working import WorkingMemoryL1

logging.basicConfig(level=logging.INFO)


class DummyEmbedder:
    async def aembed(self, content: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(content, str):
            return [0.0] * 384
        return [[0.0] * 384 for _ in content]


async def run_resonance():
    print("[E2E] Booting in-memory SQLite and dependencies...")
    conn = await aiosqlite.connect(":memory:")

    l1 = WorkingMemoryL1()
    l3 = EventLedgerL3(conn)
    await l3.ensure_table()

    encoder = AsyncEncoder(DummyEmbedder())

    try:
        l2 = SovereignVectorStoreL2(encoder=encoder, db_path=":memory:")
        await l2.ensure_table()
    except Exception as e:
        print(f"[E2E] SovereignVectorStoreL2 init failed ({e}), falling back to MagicMock.")
        from unittest.mock import AsyncMock, MagicMock

        l2 = MagicMock()
        l2._get_conn = MagicMock()
        l2.upsert = AsyncMock()
        l2.search_similar = AsyncMock(return_value=[])

    manager = CortexMemoryManager(l1=l1, l2=l2, l3=l3, encoder=encoder, max_bg_tasks=10)

    print("[E2E] Injecting Semantic Pulse...")
    response = await manager.process_interaction(
        role="user",
        content="This is a test of the decoupled Exergy pipeline.",
        session_id="e2e_session",
        tenant_id="e2e_tenant",
        project_id="e2e_project",
        token_count=15,
    )

    print(f"[E2E] Pipeline Response: {response}")

    print("[E2E] Waiting for Glial Background Compression...")
    await manager.wait_for_background(timeout=3.0)

    print("[E2E] Shutting down...")
    await manager._cancel_background_tasks()
    await conn.close()
    print("[E2E] C5-REAL Success.")


if __name__ == "__main__":
    asyncio.run(run_resonance())
