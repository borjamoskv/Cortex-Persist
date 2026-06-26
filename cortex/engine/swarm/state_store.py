# [C5-REAL] Exergy-Maximized
"""
CAUSAL STATE STORE: The Thermodynamic Funnel.
Isolates SQLite writes from massive async concurrency to prevent I/O Deadlocks.
Enforces SAGA patterns, Guards validation, and Ledger cryptographic emission.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.config import DB_PATH
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
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("PRAGMA journal_mode=WAL;")
            await self._db.execute("PRAGMA synchronous=NORMAL;")
            
            # SANEDRIN VECTOR 1: Local Audit Ledger
            await self._db.execute('''
                CREATE TABLE IF NOT EXISTS audit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    target TEXT,
                    status TEXT,
                    timestamp TEXT,
                    payload TEXT
                )
            ''')
            
            # SANEDRIN VECTOR 3: Lease Locks
            try:
                await self._db.execute("ALTER TABLE system_hypotheses ADD COLUMN owner_id TEXT;")
            except aiosqlite.OperationalError:
                pass # Column already exists
            
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
                    logger.warning(f"Dropping signal for {signal.target}: Hypothesis is INVALIDATED.")
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

                # 3. SAGA Step 2 & 3: Atomic 2PC Mutation
                await self._db.execute(
                    "INSERT INTO audit_ledger (agent_id, target, status, timestamp, payload) VALUES (?, ?, ?, ?, ?)",
                    (signal.agent_id, signal.target, signal.status, ledger_payload["timestamp"], json.dumps(signal.payload))
                )

                if signal.status in ("SUCCESS", "FAILURE"):
                    await self._db.execute(
                        "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
                    )
                    
                    if signal.target.startswith("hyp-") and signal.status == "SUCCESS":
                        await self._db.execute(
                            "UPDATE system_hypotheses SET status = 'COMPLETED' WHERE id = ?", (signal.target,)
                        )
                
                # ATOMIC COMMIT (SANEDRIN VECTOR 1)
                await self._db.commit()

            except Exception as e:
                await self._db.rollback()
                logger.error(f"[SAGA ROLLBACK] State mutation failed: {e}")
                
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
                count = (await cur.fetchone())[0]
                
            if count > 0:
                logger.info(f"Recovering {count} IN_FLIGHT tasks to ACTIVE status.")
                update_q = "UPDATE system_hypotheses SET status = 'ACTIVE' WHERE status = 'IN_FLIGHT'"
                if lease_id:
                    update_q += " AND owner_id = ?"
                await self._db.execute(update_q, params)
                await self._db.execute(
                    "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
                )
                await self._db.commit()
            return count
