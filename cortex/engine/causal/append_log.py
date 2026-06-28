import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.engine.causal.aol")

AOL_FILE = Path("/tmp/cortex_ledger.aol")


class AppendOnlyLog:
    """Zero-block I/O append log for the Swarm Supervisor (C5-REAL)."""

    @classmethod
    def append_batch(cls, mutations: list[dict[str, Any]]) -> None:
        """Appends a batch of state mutations to the log file synchronously.
        Leverages OS page caching for nanosecond-level non-blocking I/O.
        """
        if not mutations:
            return

        with open(AOL_FILE, "a", encoding="utf-8") as f:
            for mut in mutations:
                f.write(json.dumps(mut) + "\n")


class CrystallizerDaemon:
    """Background worker that drains the AOL and writes to SQLite asynchronously.
    Enforces the CQRS pattern to prevent Single-Writer database lock contention.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._running = False
        self._task = None

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[Crystallizer] AOL Daemon started. SQLite CQRS enabled.")

    async def stop(self):
        self._running = False
        if self._task:
            await self._task

    async def _loop(self):
        from cortex.database.core import causal_write, connect_async

        db = await connect_async(self.db_path)
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=5000;")

        while self._running:
            try:
                await asyncio.sleep(1.0)  # Drain every 1 second

                if not AOL_FILE.exists() or AOL_FILE.stat().st_size == 0:
                    continue

                # Atomically move the file to process it
                processing_file = AOL_FILE.with_suffix(".processing")
                try:
                    AOL_FILE.rename(processing_file)
                except FileNotFoundError:
                    continue

                mutations = []
                with open(processing_file, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            mutations.append(json.loads(line))

                if not mutations:
                    processing_file.unlink()
                    continue

                # Batch group by table
                audit_params = []
                hypo_updates = []
                meta_version_inc = 0
                facts_inserts = []

                for mut in mutations:
                    if mut["table"] == "audit_ledger":
                        audit_params.append(mut["params"])
                    elif mut["table"] == "system_hypotheses":
                        hypo_updates.append(mut["params"])
                        meta_version_inc += 1
                    elif mut["table"] == "facts":
                        facts_inserts.append(mut["params"])

                with causal_write(db):
                    if audit_params:
                        await db.executemany(
                            "INSERT INTO audit_ledger (agent_id, target, status, timestamp, payload) VALUES (?, ?, ?, ?, ?)",
                            audit_params,
                        )
                    if hypo_updates:
                        await db.executemany(
                            "UPDATE system_hypotheses SET status = 'COMPLETED' WHERE id = ?",
                            hypo_updates,
                        )
                    if meta_version_inc > 0:
                        await db.execute(
                            "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + ? AS TEXT) WHERE key = 'hypothesis_graph_version'",
                            (meta_version_inc,),
                        )
                    if facts_inserts:
                        await db.executemany(
                            "INSERT INTO facts (tenant_id, project, content, fact_type, confidence, source, metadata, is_tombstoned) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            facts_inserts,
                        )
                    await db.commit()

                processing_file.unlink()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Crystallizer] AOL Drain failed: {e}")
                # Rollback file state safely
                if "processing_file" in locals() and processing_file.exists():
                    with open(AOL_FILE, "a", encoding="utf-8") as f_out:
                        with open(processing_file, encoding="utf-8") as f_in:
                            f_out.write(f_in.read())
                    processing_file.unlink()
                await asyncio.sleep(5.0)  # Backoff

        await db.close()
