# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import pytest

# Mark the test as slow since initializing/running CortexEngine takes some time
pytestmark = pytest.mark.slow


@pytest.fixture
async def engine(tmp_path: Path):
    """Create a CortexEngine with a temp database, close after test."""
    from legacy_research.engine import CortexEngine

    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    db = str(tmp_path / "test_concurrency.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()

    # Ensure causal_edges exists
    from legacy_research.engine.causality import AsyncCausalGraph

    async with e.session() as conn:
        cg = AsyncCausalGraph(conn)
        await cg.ensure_table()

    yield e
    await e.close()
    if "CORTEX_SKIP_EXERGY_VALIDATION" in os.environ:
        del os.environ["CORTEX_SKIP_EXERGY_VALIDATION"]


async def run_concurrent_appends(engine, n_writers: int) -> list[int]:
    """Spawn concurrent appends to log transactions under stress."""

    async def append_one(i: int) -> int:
        async with engine.session() as conn:
            tx_id = await engine._log_transaction(
                conn,
                project="concurrency_test",
                action="append",
                detail={"writer_index": i},
                tenant_id="default",
            )
            await conn.commit()
            return tx_id

    tasks = [append_one(i) for i in range(n_writers)]
    return await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_ledger_append_concurrency_serialization(engine) -> None:
    """CON-01A Regression Test: Run concurrent append transactions.

    Runs 10 consecutive rounds of concurrent writes (50 tasks each).
    Verifies linearizable chain integrity and determinism at the end of each round.
    """
    n_rounds = 10
    n_writers_per_round = 50

    for round_idx in range(n_rounds):
        # 1. Run concurrent appends
        tx_ids = await run_concurrent_appends(engine, n_writers_per_round)
        assert len(tx_ids) == n_writers_per_round
        assert len(set(tx_ids)) == n_writers_per_round, "All tx_ids must be unique"

        # 2. Query and verify the entire chain from the database
        async with engine.session() as conn:
            async with conn.execute(
                "SELECT id, prev_hash, hash, detail FROM transactions WHERE tenant_id = 'default' ORDER BY id ASC"
            ) as cursor:
                rows = await cursor.fetchall()

            # Verify the total rows match the accumulated count
            expected_total = (round_idx + 1) * n_writers_per_round
            assert len(rows) == expected_total, f"Expected {expected_total} rows, found {len(rows)}"

            # Verify perfect linear linkage
            prev_hash_tracker = {}
            for i, row in enumerate(rows):
                tx_id, prev_hash, current_hash, detail = row

                # Verify predecessor linkage
                if i == 0:
                    assert prev_hash == "GENESIS", "First transaction must link to GENESIS"
                else:
                    expected_prev = rows[i - 1][2]  # previous row's hash
                    assert prev_hash == expected_prev, (
                        f"Row {i} (ID {tx_id}) broke hash link! "
                        f"Expected prev_hash {expected_prev}, got {prev_hash}"
                    )

                # Verify no duplicate predecessor hashes
                assert prev_hash not in prev_hash_tracker, (
                    f"Duplicate predecessor hash detected at ID {tx_id}: {prev_hash}"
                )
                prev_hash_tracker[prev_hash] = tx_id

        # 3. Perform programmatic audit verify_ledger check
        report = await engine.verify_ledger()
        assert report["valid"] is True, (
            f"Ledger audit integrity failed at round {round_idx}: {report.get('violations')}"
        )
