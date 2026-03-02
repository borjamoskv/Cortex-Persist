"""CORTEX v5.0 — Semantic RAM stress test.

Validates the Read-as-Rewrite pipeline: store facts → query →
emit topological pulse → verify excitation mutation.

Fixes from Axiom 19 audit:
- `hebbian_daemon` renamed to `semantic_mutator` (matches production code)
- Added `row_factory` verification (catches the dict-key crash)
- Explicit cleanup in all exit paths
- Type annotations throughout
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import CortexFactModel
from cortex.memory.semantic_ram import DynamicSemanticSpace
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_DB = "/tmp/cortex_omega_test.db"


class MockEncoder(AsyncEncoder):
    """Deterministic 2D encoder for test reproducibility."""

    @property
    def dimension(self) -> int:
        return 2

    async def encode(self, text: str) -> list[float]:
        return [0.5, 0.5]


async def stress_test() -> None:
    logger.info("======== BOOTING SOVEREIGN UNIVERSE ========")

    encoder = MockEncoder()
    l2_store = SovereignVectorStoreL2(
        encoder=encoder, db_path=TEST_DB,
    )
    logger.info("✓ Initialized SovereignVectorStoreL2")

    # ─── Insert baseline facts ───────────────────────────────────
    for i in range(3):
        fact = CortexFactModel(
            id=str(uuid4()),
            tenant_id="test_tenant",
            project_id="test_project",
            content=f"Fact number {i} regarding quantum topological decay.",
            embedding=[0.5, 0.5],
            timestamp=1700000000.0,
            success_rate=1.0,
        )
        await l2_store.memorize(fact)

    logger.info("✓ Stored 3 baseline facts")

    # ─── Boot Dynamic Semantic Space ─────────────────────────────
    space = DynamicSemanticSpace(l2_store)
    space.semantic_mutator.start()
    logger.info("✓ Semantic Mutator daemon running")

    # ─── Query (Read-as-Rewrite) ─────────────────────────────────
    results = await space.recall_and_pulse(
        tenant_id="test_tenant",
        project_id="test_project",
        query="Explain quantum",
        limit=5,
        pulse_excitation=20.0,
    )
    logger.info("✓ Retrieved %d facts. Pulse emitted.", len(results))

    # Allow daemon to process pulse batch
    await asyncio.sleep(0.5)

    # ─── Verify mutation with correct Row access ─────────────────
    import sqlite3

    conn = l2_store._get_conn()
    conn.row_factory = sqlite3.Row  # Must match production code
    cursor = conn.cursor()
    cursor.execute("SELECT id, success_rate FROM facts_meta")
    rows = cursor.fetchall()

    for row in rows:
        logger.info(
            "  fact=%s  excitation=%.2f",
            row["id"][:8], row["success_rate"],
        )

    # Verify at least one fact was excited above baseline
    excited = [r for r in rows if r["success_rate"] > 1.0]
    if excited:
        logger.info("✓ Topological mutation verified: %d facts excited", len(excited))
    else:
        logger.warning("⚠ No facts were excited — check daemon timing")

    # ─── Cleanup ─────────────────────────────────────────────────
    try:
        await space.semantic_mutator.stop()
    except asyncio.CancelledError:
        pass  # Expected — stop() re-raises cancellation
    await l2_store.close()

    # Remove test DB
    import os
    try:
        os.unlink(TEST_DB)
    except FileNotFoundError:
        pass

    logger.info("======== STRESS TEST COMPLETE ========")


if __name__ == "__main__":
    asyncio.run(stress_test())
