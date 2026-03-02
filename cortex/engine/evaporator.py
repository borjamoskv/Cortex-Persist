"""Entropic Evaporator — Ω₂: Selective Forgetting (Evaporation).

Space is finite. Knowledge has a half-life. This engine prunes 
low-value, unverified, and non-causal facts to reduce system heat.
"""

from __future__ import annotations
import logging
import aiosqlite
from datetime import datetime, timedelta

from cortex.engine.mutation_engine import MUTATION_ENGINE
from cortex.memory.temporal import now_iso

logger = logging.getLogger("cortex.evaporator")

class EntropicEvaporator:
    """Prunes facts that contribute more to noise than to utility."""

    def __init__(self, db_conn: aiosqlite.Connection):
        self._conn = db_conn

    async def evaporate(self) -> int:
        """
        Scans for facts that satisfy the evaporation criteria:
        1. Age > 30 days.
        2. Confidence == 'stated' (never verified/disputed).
        3. No causal parent (orphaned insight).
        4. No 'axiom' or 'decision' type.
        """
        logger.info("💨 [EVAPORATOR] Starting evaporation cycle (Ω₂)...")
        
        limit_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        # We query for candidate IDs
        # meta NOT LIKE '%causal_parent%' is a heuristic check on encrypted/raw meta
        # Note: In a real scenario with full encryption, we'd need a way to check
        # without decrypting everything, but here we favor the principle.
        
        query = """
            SELECT id, tenant_id FROM facts
            WHERE valid_until IS NULL
            AND fact_type NOT IN ('axiom', 'decision', 'bridge')
            AND confidence = 'stated'
            AND created_at < ?
            AND (meta IS NULL OR meta NOT LIKE '%causal_parent%')
        """
        
        candidates = []
        async with self._conn.execute(query, (limit_date,)) as cursor:
            async for row in cursor:
                candidates.append((row[0], row[1]))

        count = 0
        for fact_id, tenant_id in candidates:
            await MUTATION_ENGINE.apply(
                self._conn,
                fact_id=fact_id,
                tenant_id=tenant_id,
                event_type="deprecate",
                payload={"reason": "evaporated", "axiom": "Ω₂", "ts": now_iso()},
                signer="engine:evaporator",
                commit=False
            )
            count += 1

        if count > 0:
            await self._conn.commit()
            logger.info("💨 [EVAPORATOR] Evaporated %d thermal parasites.", count)
            
        return count
