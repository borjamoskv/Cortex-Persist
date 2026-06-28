# [C5-REAL] Exergy-Maximized
"""
CAUSAL STATE STORE: The Thermodynamic Funnel.
Isolates SQLite writes from massive async concurrency to prevent I/O Deadlocks.
Enforces SAGA patterns, Guards validation, and Ledger cryptographic emission.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.config import DB_PATH
from cortex.database.core import causal_write, connect_async
from cortex.guards import CausalClosureGuard, SwarmProposal

# Replace with correct import for Ledger if needed, but the old code emitted SwarmProposal.

logger = logging.getLogger(__name__)


class CausalStateStore:
    """The only component authorized to write causal state to SQLite."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self):
        if not self._db:
            self._db = await connect_async(self.db_path)
            await self._db.execute("PRAGMA journal_mode=WAL;")
            await self._db.execute("PRAGMA synchronous=NORMAL;")
            await self._db.execute("PRAGMA busy_timeout=5000;")

            # SANEDRIN VECTOR 1: Local Audit Ledger
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS audit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    target TEXT,
                    status TEXT,
                    timestamp TEXT,
                    payload TEXT
                )
            """)

            # SANEDRIN VECTOR 3: Lease Locks
            try:
                await self._db.execute("ALTER TABLE system_hypotheses ADD COLUMN owner_id TEXT;")
            except aiosqlite.OperationalError:
                pass  # Column already exists

            try:
                await self._db.execute(
                    "ALTER TABLE system_hypotheses ADD COLUMN lease_expires_at TEXT;"
                )
            except aiosqlite.OperationalError:
                pass  # Column already exists

            await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def _verify_hypothesis_active(self, hyp_id: str) -> bool:
        if not self._db:
            return False
        async with self._db.execute(
            "SELECT status FROM system_hypotheses WHERE id = ?", (hyp_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == "INVALIDATED":
                return False
        return True

    async def process_signal(self, signal: Any) -> None:
        """Process a SwarmSignal, validate guards, and commit to state."""
        await self.connect()
        async with self._lock:
            if not self._db:
                raise RuntimeError("Database not connected.")

            # 1. Hito 2: Cascade Death Protection
            if signal.target.startswith("hyp-"):
                is_active = await self._verify_hypothesis_active(signal.target)
                if not is_active:
                    logger.warning(
                        f"Dropping signal for {signal.target}: Hypothesis is INVALIDATED."
                    )
                    return

            try:
                # 2. SAGA Step 1: Ledger cryptographic validation
                ledger_payload = {
                    "type": "CausalStateMutation",
                    "agent_id": signal.agent_id,
                    "target": signal.target,
                    "status": signal.status,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "payload": signal.payload,
                }

                proposal = SwarmProposal(
                    agent_id=signal.agent_id,
                    mission_statement=f"Apply signal to {signal.target}",
                    content=json.dumps(ledger_payload),
                    token_cost=100,
                )
                guard = CausalClosureGuard()
                guard.verify_closure(proposal)

                # SAGA Step 1.5: Cryptographic Taint Validation (APEX-002)
                from cortex.engine.causal.taint_engine import enforce_taint_check

                taint_token = getattr(signal, "taint_token", None)
                if (
                    not taint_token
                    and hasattr(signal, "metadata")
                    and isinstance(signal.metadata, dict)
                ):
                    taint_token = signal.metadata.get("taint_token")

                await enforce_taint_check(self._db, taint_token, json.dumps(signal.payload))

                # 3. SAGA Step 2 & 3: Atomic 2PC Mutation
                with causal_write(self._db):
                    await self._db.execute(
                        "INSERT INTO audit_ledger (agent_id, target, status, timestamp, payload) VALUES (?, ?, ?, ?, ?)",
                        (
                            signal.agent_id,
                            signal.target,
                            signal.status,
                            ledger_payload["timestamp"],
                            json.dumps(signal.payload),
                        ),
                    )

                    if signal.status in ("SUCCESS", "FAILURE"):
                        await self._db.execute(
                            "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
                        )

                        if signal.target.startswith("hyp-") and signal.status == "SUCCESS":
                            await self._db.execute(
                                "UPDATE system_hypotheses SET status = 'COMPLETED' WHERE id = ?",
                                (signal.target,),
                            )

                            # EPISTEMIC LOOP CLOSURE: Output becomes RawEvidence
                            try:
                                from cortex.extensions.skills.autodidact.epistemology import (
                                    EvidenceSource,
                                    RawEvidence,
                                )

                                raw_ev = RawEvidence(
                                    source=EvidenceSource.KERNEL_EVENTS,
                                    raw_payload=signal.payload,
                                    timestamp_iso=ledger_payload["timestamp"],
                                )
                                # Directly inject into raw epistemological stream (bypass engine indexes for speed, rely on async consolidators)
                                await self._db.execute(
                                    "INSERT INTO facts (tenant_id, project, content, fact_type, confidence, source, metadata, is_tombstoned) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (
                                        "default",
                                        "global",
                                        raw_ev.model_dump_json(),
                                        "raw_evidence",
                                        "C5-REAL",
                                        f"sanedrin:{signal.agent_id}",
                                        "{}",
                                        0,
                                    ),
                                )
                            except Exception as epi_e:
                                logger.warning(
                                    f"[EpistemicBreaker] Failed to compile RawEvidence from {signal.target}: {epi_e}"
                                )

                    # ATOMIC COMMIT (SANEDRIN VECTOR 1)
                    await self._db.commit()

            except (aiosqlite.Error, ValueError, KeyError, TypeError, RuntimeError) as e:
                await self._db.rollback()
                logger.error(f"[SAGA ROLLBACK] State mutation failed: {e}")

    async def process_signals_batch(self, signals: list[Any]) -> None:
        """Process a batch of SwarmSignals, validate guards, and commit to state atomically."""
        await self.connect()
        async with self._lock:
            if not self._db:
                raise RuntimeError("Database not connected.")

            valid_signals = []
            for signal in signals:
                if signal.target.startswith("hyp-"):
                    is_active = await self._verify_hypothesis_active(signal.target)
                    if not is_active:
                        logger.warning(
                            f"Dropping signal for {signal.target}: Hypothesis is INVALIDATED."
                        )
                        continue

                try:
                    ledger_payload = {
                        "type": "CausalStateMutation",
                        "agent_id": signal.agent_id,
                        "target": signal.target,
                        "status": signal.status,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "payload": signal.payload,
                    }

                    proposal = SwarmProposal(
                        agent_id=signal.agent_id,
                        mission_statement=f"Apply signal to {signal.target}",
                        content=json.dumps(ledger_payload),
                        token_cost=100,
                    )
                    guard = CausalClosureGuard()
                    guard.verify_closure(proposal)

                    from cortex.engine.causal.taint_engine import enforce_taint_check

                    taint_token = getattr(signal, "taint_token", None)
                    if (
                        not taint_token
                        and hasattr(signal, "metadata")
                        and isinstance(signal.metadata, dict)
                    ):
                        taint_token = signal.metadata.get("taint_token")

                    await enforce_taint_check(self._db, taint_token, json.dumps(signal.payload))
                    valid_signals.append((signal, ledger_payload))

                except Exception as e:
                    logger.error(f"[SAGA REJECT] Signal validation failed for {signal.target}: {e}")
                    continue

            if not valid_signals:
                return

            try:
                # 3. SAGA Step 2 & 3: Atomic AOL Append (Bypass SQLite Lock)
                mutations = []
                for s, lp in valid_signals:
                    mutations.append(
                        {
                            "table": "audit_ledger",
                            "params": (
                                s.agent_id,
                                s.target,
                                s.status,
                                lp["timestamp"],
                                json.dumps(s.payload),
                            ),
                        }
                    )

                    if s.status in ("SUCCESS", "FAILURE"):
                        if s.target.startswith("hyp-") and s.status == "SUCCESS":
                            mutations.append({"table": "system_hypotheses", "params": (s.target,)})

                            try:
                                from cortex.extensions.skills.autodidact.epistemology import (
                                    EvidenceSource,
                                    RawEvidence,
                                )

                                raw_ev = RawEvidence(
                                    source=EvidenceSource.KERNEL_EVENTS,
                                    raw_payload=s.payload,
                                    timestamp_iso=lp["timestamp"],
                                )
                                mutations.append(
                                    {
                                        "table": "facts",
                                        "params": (
                                            "default",
                                            "global",
                                            raw_ev.model_dump_json(),
                                            "raw_evidence",
                                            "C5-REAL",
                                            f"sanedrin:{s.agent_id}",
                                            "{}",
                                            0,
                                        ),
                                    }
                                )
                            except Exception as epi_e:
                                logger.warning(
                                    f"[EpistemicBreaker] Failed to compile RawEvidence from {s.target}: {epi_e}"
                                )

                if mutations:
                    from cortex.engine.causal.append_log import AppendOnlyLog

                    AppendOnlyLog.append_batch(mutations)

            except Exception as e:
                logger.error(f"[SAGA ROLLBACK] Batch AOL mutation failed: {e}")

    async def recover_in_flight_tasks(self, lease_id: str | None = None) -> int:
        """SANEDRIN VECTOR 3: Lease-locked Ghost Recovery."""
        await self.connect()
        async with self._lock:
            if not self._db:
                return 0

            query = "SELECT count(*) FROM system_hypotheses WHERE status = 'IN_FLIGHT'"
            params = []
            if lease_id:
                query += " AND owner_id = ?"
                params.append(lease_id)

            async with self._db.execute(query, params) as cur:
                count = (await cur.fetchone())[0]  # type: ignore

            if count > 0:
                logger.info(f"Recovering {count} IN_FLIGHT tasks to ACTIVE status.")
                update_q = "UPDATE system_hypotheses SET status = 'ACTIVE', owner_id = NULL, lease_expires_at = NULL WHERE status = 'IN_FLIGHT'"
                if lease_id:
                    update_q += f" AND owner_id = '{lease_id}'"
                with causal_write(self._db):
                    await self._db.execute(update_q)
                    await self._db.execute(
                        "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
                    )
                    await self._db.commit()
            return count

    async def sweep_expired_leases(self) -> int:
        """SANEDRIN VECTOR 3: Sweeps expired lease locks to prevent orphan task deadlocks."""
        await self.connect()
        async with self._lock:
            if not self._db:
                return 0

            now_iso = datetime.now(timezone.utc).isoformat()
            query = "UPDATE system_hypotheses SET status = 'ACTIVE', owner_id = NULL, lease_expires_at = NULL WHERE status = 'IN_FLIGHT' AND lease_expires_at IS NOT NULL AND lease_expires_at < ?"

            from cortex.database.core import causal_write

            with causal_write(self._db):
                async with self._db.execute(query, (now_iso,)) as cur:
                    count = cur.rowcount

                await self._db.commit()

                if count > 0:
                    logger.warning(
                        f"[SANEDRIN] Swept {count} expired lease locks. Ghost tasks recovered."
                    )

            return count
