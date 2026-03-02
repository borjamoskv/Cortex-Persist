"""
Integration test for CORTEX Nexus v8.1 — Production Grade.
Tests: SQLite WAL persistence, idempotency dedup, priority ordering,
parallel hooks, and cross-domain query interface.
"""

import asyncio
import logging
import os
import time

from cortex.nexus_v8 import (
    NexusWorldModel,
    DomainOrigin,
    IntentType,
    Priority,
    WorldMutation,
    mailtv_intercepted,
    moltbook_post_published,
    moltbook_karma_laundered,
    moltbook_shadowban_alert,
    sap_anomaly_detected,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_DB = "/tmp/nexus_v8_test.db"

# ─── Hook Tracking ───────────────────────────────────────────────────

hook_log: list[str] = []


async def hook_moltbook_react(mutation: WorldMutation) -> None:
    hook_log.append(f"MOLTBOOK:{mutation.intent.name}")


async def hook_sap_audit(mutation: WorldMutation) -> None:
    hook_log.append(f"SAP:{mutation.intent.name}")


async def hook_slow_llm(mutation: WorldMutation) -> None:
    """Simulates a slow hook (LLM call). Should NOT block other hooks."""
    await asyncio.sleep(0.3)
    hook_log.append(f"SLOW_LLM:{mutation.intent.name}")


async def run_tests():
    # Clean slate
    for f in [TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"]:
        if os.path.exists(f):
            os.remove(f)

    logger.info("=" * 60)
    logger.info("NEXUS v8.1 — PRODUCTION INTEGRATION TEST")
    logger.info("=" * 60)

    nexus = NexusWorldModel(db_path=TEST_DB)

    # ─── TEST 1: Cross-domain hooks fire in parallel ─────────────
    nexus.on(IntentType.EMAIL_INTERCEPTED, hook_moltbook_react)
    nexus.on(IntentType.EMAIL_INTERCEPTED, hook_sap_audit)
    nexus.on(IntentType.EMAIL_INTERCEPTED, hook_slow_llm)

    t0 = time.monotonic()
    result = await mailtv_intercepted(
        nexus,
        sender="sergio@gordacorp.com",
        subject="Re: SAP Fase 2",
        confidence=92.0,
        action="DRAFT_AND_NOTIFY",
        cortex_hits=3,
    )
    elapsed = time.monotonic() - t0

    assert result is True, "Mutation should be applied"
    assert len(hook_log) == 3, f"Expected 3 hooks, got {len(hook_log)}"
    # If hooks ran in parallel, total time < sum of all hook times
    assert elapsed < 1.0, f"Hooks should run in parallel, took {elapsed:.2f}s"
    logger.info("✓ TEST 1: Parallel hooks (%d fired in %.2fs)", len(hook_log), elapsed)

    # ─── TEST 2: Idempotency dedup ──────────────────────────────
    hook_log.clear()
    result2 = await mailtv_intercepted(
        nexus,
        sender="sergio@gordacorp.com",
        subject="Re: SAP Fase 2",
        confidence=92.0,
        action="DRAFT_AND_NOTIFY",
        cortex_hits=3,
    )
    assert result2 is False, "Duplicate mutation should be rejected"
    assert len(hook_log) == 0, "Hooks should NOT fire for duplicates"
    assert nexus.stats["deduplicated"] >= 1
    logger.info("✓ TEST 2: Idempotency dedup (duplicate rejected)")

    # ─── TEST 3: Priority ordering ──────────────────────────────
    await moltbook_post_published(
        nexus, agent_name="DEBUGGER", submolt="cortex",
        title="Test Post", karma_before=10.0,
    )
    await moltbook_shadowban_alert(
        nexus, agent_name="INGENUE", evidence="Visibility -80%",
    )
    await sap_anomaly_detected(
        nexus, module="FI-GL", severity="HIGH",
        description="Duplicate posting in P12",
    )

    # Query with priority ordering (CRITICAL first)
    all_mutations = await nexus.query(limit=100)
    priorities = [r["priority"] for r in all_mutations]
    assert priorities == sorted(priorities), f"Should be sorted by priority: {priorities}"
    logger.info("✓ TEST 3: Priority ordering (CRITICAL → LOW)")

    # ─── TEST 4: Query interface ─────────────────────────────────
    moltbook_events = await nexus.query(origin=DomainOrigin.MOLTBOOK)
    assert len(moltbook_events) >= 2, f"Expected ≥2 Moltbook events, got {len(moltbook_events)}"

    critical_events = await nexus.query(intent=IntentType.SHADOWBAN_DETECTED)
    assert len(critical_events) == 1
    assert critical_events[0]["priority"] == Priority.CRITICAL.value

    logger.info("✓ TEST 4: Query interface (filtered by origin, intent)")

    # ─── TEST 5: SQLite persistence (cross-process simulation) ──
    # Create a second NexusWorldModel pointing to the same DB
    nexus2 = NexusWorldModel(db_path=TEST_DB)
    cross_process_query = await nexus2.query(limit=100)
    assert len(cross_process_query) == len(all_mutations), \
        "Second process should see same mutations"
    logger.info("✓ TEST 5: Cross-process persistence (%d mutations visible)", len(cross_process_query))

    # ─── TEST 6: Mutation count ──────────────────────────────────
    assert nexus.mutation_count == 4, f"Expected 4 stored, got {nexus.mutation_count}"
    logger.info("✓ TEST 6: Mutation count = %d", nexus.mutation_count)

    # ─── TEST 7: Stats ──────────────────────────────────────────
    stats = nexus.stats
    assert stats["total_mutations"] == 4
    assert stats["deduplicated"] >= 1
    assert stats["hook_fires"] == 3
    logger.info("✓ TEST 7: Stats verified: %s", stats)

    # Shutdown
    await nexus.shutdown()
    await nexus2.shutdown()

    # Cleanup
    for f in [TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"]:
        if os.path.exists(f):
            os.remove(f)

    logger.info("=" * 60)
    logger.info("ALL 7 TESTS PASSED — THE BRIDGE IS PRODUCTION-GRADE")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
