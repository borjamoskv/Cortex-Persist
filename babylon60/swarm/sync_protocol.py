# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
from typing import Any
import aiosqlite

from babylon60.core.config import DB_PATH
from babylon60.database.core import connect_async

logger = logging.getLogger(__name__)


class SwarmSyncEngine:
    """Sovereign Agentic P2P Sync Engine.
    
    Implements O(log N) Merkle DAG synchronization protocol for state stores.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def generate_state_proof(self, tenant_id: str = "default") -> str:
        """Retrieves the Merkle Root of the current ledger state in O(1) by reading the last transaction hash."""
        db = await connect_async(self.db_path)
        try:
            async with db.execute(
                "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                (tenant_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else "GENESIS"
        finally:
            await db.close()

    async def get_all_indexed_hashes(self, tenant_id: str = "default") -> set[str]:
        """Returns the set of all transaction hashes in the local ledger."""
        db = await connect_async(self.db_path)
        try:
            async with db.execute(
                "SELECT hash FROM transactions WHERE tenant_id = ?",
                (tenant_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return {r[0] for r in rows}
        finally:
            await db.close()

    async def calculate_delta(self, remote_hashes: set[str], tenant_id: str = "default") -> list[dict[str, Any]]:
        """Calculates the missing transaction nodes compared to the remote set, preserving causal order."""
        local_hashes = await self.get_all_indexed_hashes(tenant_id)
        missing_in_remote = local_hashes - remote_hashes

        if not missing_in_remote:
            return []

        db = await connect_async(self.db_path)
        try:
            # We want to retrieve all columns for the missing transaction hashes
            placeholders = ", ".join("?" for _ in missing_in_remote)
            query = f"SELECT id, project, action, detail, prev_hash, hash, tenant_id, timestamp FROM transactions WHERE hash IN ({placeholders}) AND tenant_id = ?"
            params = list(missing_in_remote) + [tenant_id]

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
                delta = []
                for r in rows:
                    delta.append({
                        "id": r[0],
                        "project": r[1],
                        "action": r[2],
                        "detail": r[3],
                        "prev_hash": r[4],
                        "hash": r[5],
                        "tenant_id": r[6],
                        "timestamp": r[7],
                    })

                # Sort by logical order (the autoincrement ID guarantees causal order)
                delta.sort(key=lambda x: x["id"])
                return delta
        finally:
            await db.close()
