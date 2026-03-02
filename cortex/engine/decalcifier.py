"""
CORTEX V7 — Sovereign Decalcifier (Protocol Ω₃-E).

Prevents 'fossilization' of beliefs by decaying consensus scores and triggering
active re-verification pulses.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from cortex.engine.mutation_engine import MUTATION_ENGINE

if TYPE_CHECKING:
    from aiosqlite import Connection

logger = logging.getLogger("cortex.decalcifier")

DEFAULT_DECAY_INTERVAL_MIN = 1440  # 24 hours
DEFAULT_DECAY_FACTOR = 0.98


class SovereignDecalcifier:
    """Background engine to maintain epistemic humility (Protocol Ω₃-E)."""

    def __init__(
        self,
        interval_min: int = DEFAULT_DECAY_INTERVAL_MIN,
        decay_factor: float = DEFAULT_DECAY_FACTOR,
    ) -> None:
        self.interval = interval_min * 60
        self.decay_factor = decay_factor
        self._is_active = False

    async def start(self, conn_func: callable) -> None:
        """Start the decalcification cycle."""
        if self._is_active:
            return
        self._is_active = True
        logger.info("🧬 [Ω₃-E] Decalcifier online. Entropy gradient active.")

        while self._is_active:
            try:
                await self.decalcify_cycle(await conn_func())
            except Exception as e:
                logger.error("Decalcifier failure: %s", e)
            await asyncio.sleep(self.interval)

    async def decalcify_cycle(self, conn: Connection) -> int:
        """Scan for stale verified facts and apply decay."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=self.interval)).isoformat()

        # Find stale verified facts
        cursor = await conn.execute(
            """
            SELECT id, tenant_id, consensus_score FROM facts 
            WHERE confidence = 'verified' AND updated_at < ?
            """,
            (cutoff,),
        )
        stale_facts = await cursor.fetchall()

        count = 0
        for fact_id, tenant_id, score in stale_facts:
            await MUTATION_ENGINE.apply(
                conn,
                fact_id=fact_id,
                tenant_id=tenant_id,
                event_type="decalcify",
                payload={
                    "decay_factor": self.decay_factor,
                    "reason": "Protocol Ω₃-E Periodic Decay",
                },
                signer="sovereign_decalcifier",
                commit=False,
            )
            count += 1

        if count > 0:
            await conn.commit()
            logger.info("🧬 [Ω₃-E] Decalcified %d stagnant facts. Entropy restored.", count)

        return count

    def stop(self) -> None:
        """Halt decalcification."""
        self._is_active = False
        logger.info("🧬 [Ω₃-E] Decalcifier suspended. State freezing.")
