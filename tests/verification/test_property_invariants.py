# [C5-REAL] Exergy-Maximized
import asyncio
import os
import sqlite3
from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from babylon60.engine.core.cortex_engine import CortexEngine
from babylon60.engine.flow.storage_guard import GuardViolation


@settings(max_examples=25, deadline=None)
class CortexStoreMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()

        self.old_exergy = os.environ.get("CORTEX_SKIP_EXERGY_VALIDATION")
        self.old_taint = os.environ.get("CORTEX_NO_TAINT_ENFORCE")

        # Setup temporary database
        self.db_path = f"cortex_hypothesis_{id(self)}.db"
        # Temporarily bypass exergy to allow fast property testing without LLMs
        os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
        os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"

        self.engine = CortexEngine(db_path=self.db_path, auto_embed=False)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.engine.init_db())

        # State tracking
        self.expected_facts_count = 0
        self.expected_ledgers_count = 0  # Including saga_aborts
        self.known_projects = set()

    def teardown(self):
        self.loop.run_until_complete(self.engine.close())
        self.loop.close()
        for suffix in ("", "-wal", "-shm"):
            path = f"{self.db_path}{suffix}"
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        if self.old_exergy is not None:
            os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = self.old_exergy
        else:
            os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)

        if self.old_taint is not None:
            os.environ["CORTEX_NO_TAINT_ENFORCE"] = self.old_taint
        else:
            os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"

    @rule(
        project=st.text(min_size=1, max_size=50),
        content=st.text(min_size=1, max_size=1000),
        source=st.sampled_from(["cli"]),
    )
    def valid_store(self, project, content, source):
        """Rule representing a completely valid storage request."""

        # Check deduplication internally so we know what to expect
        async def _run():
            async with self.engine.session() as conn:
                cursor = await conn.execute(
                    "SELECT id FROM facts WHERE content = ? AND project = ? AND tenant_id = 'default'",
                    (content, project),
                )
                row = await cursor.fetchone()
                exists = bool(row)

            try:
                await self.engine.store(project=project, content=content, source=source)
                if not exists:
                    self.expected_facts_count += 1
            except Exception:
                pass

        self.loop.run_until_complete(_run())
        self._verify_chain()

    @rule(
        project=st.text(max_size=100),
        content=st.text(max_size=1000),
        source=st.text(max_size=100),  # Invalid sources allowed
    )
    def arbitrary_store(self, project, content, source):
        """Rule representing potentially invalid store requests."""

        async def _run():
            try:
                await self.engine.store(project=project, content=content, source=source)
            except Exception:
                pass

        self.loop.run_until_complete(_run())
        self._verify_chain()

    def _verify_chain(self):
        """Invariant: The cryptographic ledger chain must ALWAYS be valid."""

        async def _run():
            async with self.engine.session() as conn:
                # We can't directly use verify_ledger_chain if it relies on a specific file,
                # but we can do a quick check of the hashes here
                cursor = await conn.execute(
                    "SELECT id, prev_hash, hash, detail FROM transactions ORDER BY id ASC"
                )
                rows = await cursor.fetchall()
                if not rows:
                    return

                # Check Genesis
                assert rows[0][1] == "GENESIS", (
                    f"First transaction must point to GENESIS, but got: {rows[0]}"
                )

                # Check chain linkage
                for i in range(1, len(rows)):
                    assert rows[i][1] == rows[i - 1][2], (
                        f"Chain broken at tx {rows[i][0]}: Expected prev_hash {rows[i - 1][2]}, got {rows[i][1]}"
                    )

        self.loop.run_until_complete(_run())


# Run the stateful test
TestStoreInvariants = pytest.mark.timeout(90)(CortexStoreMachine.TestCase)
