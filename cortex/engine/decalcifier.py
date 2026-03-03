"""
CORTEX V7 — Sovereign Decalcifier (Protocol Ω₃-E+).

Prevents 'fossilization' of beliefs by decaying consensus scores and triggering
active re-verification pulses. Implements Entropic Asymmetry for weighted decay.
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
    """Background engine to maintain epistemic humility (Protocol Ω₃-E+)."""

    def __init__(
        self,
        interval_min: int = DEFAULT_DECAY_INTERVAL_MIN,
        decay_factor: float = DEFAULT_DECAY_FACTOR,
    ) -> None:
        self.interval = interval_min * 60
        self.decay_factor = decay_factor
        self._is_active = False

    async def start(self, conn_func: callable) -> None:  # type: ignore[reportGeneralTypeIssues]
        """Start the decalcification cycle."""
        if self._is_active:
            return
        self._is_active = True
        logger.info("🧬 [Ω₃-E+] Decalcifier online. Entropy gradient active.")

        while self._is_active:
            try:
                await self.decalcify_cycle(await conn_func())
            except Exception as e:
                logger.error("Decalcifier failure: %s", e)
            await asyncio.sleep(self.interval)

    async def decalcify_cycle(self, conn: Connection) -> int:
        """Scan for stale facts (Verified & Stated) and apply decay."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=self.interval)).isoformat()

        # Entropic Asymmetry (Ω₃-E+): Include 'stated' to prevent unverified noise accumulation.
        cursor = await conn.execute(
            """
            SELECT id, tenant_id, fact_type, confidence, consensus_score FROM facts
            WHERE confidence IN ('verified', 'C5', 'C4', 'C3', 'stated')
              AND is_tombstoned = 0
              AND is_quarantined = 0
              AND updated_at < ?
            """,
            (cutoff,),
        )
        stale_facts = await cursor.fetchall()

        count = 0
        for fact_id, tenant_id, fact_type, confidence, current_score in stale_facts:
            # 1. Base decay by Confidence (Stated decays faster than Verified)
            confidence_multiplier = 1.0 if confidence != "stated" else 0.95

            # 2. Type-specific entropy (Entropic Asymmetry)
            if fact_type in ("axiom", "identity", "rule"):
                type_factor = 0.999  # Absolute bedrock
            elif fact_type in ("decision", "bridge", "knowledge"):
                type_factor = 0.99   # Structural state
            elif fact_type in ("error", "ghost", "telemetry"):
                type_factor = 0.90   # Operational foam
            else:
                type_factor = self.decay_factor

            decay = type_factor * confidence_multiplier
            new_score = (current_score or 1.0) * decay

            # 3. Multi-Scale Causality (Ω₁): Ghost Elevation
            # Si un Ghost persiste a pesar del decaimiento, se eleva a Regla.
            if fact_type == "ghost" and new_score > 0.4:
                # El ruido persistente es arquitectura emergente.
                logger.warning("🧬 [Ω₁] Ghost #%s elevado a REGLA por persistencia causal.", fact_id)
                await conn.execute(
                    "UPDATE facts SET fact_type = 'rule', confidence = 'verified', "
                    "tags = json_insert(tags, '$[#]', 'elevated-ghost') WHERE id = ?",
                    (fact_id,),
                )
                continue

            # 4. Colapso Entrópico Total (Terminal Entropy)
            if new_score < 0.15 and fact_type not in ("axiom", "identity", "rule"):
                await MUTATION_ENGINE.apply(
                    conn,
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    event_type="tombstone",
                    payload={
                        "reason": f"Ω₃-E Terminal Entropy Reached ({new_score:.2f})",
                    },
                    signer="sovereign_decalcifier",
                    commit=False,
                )
            else:
                await MUTATION_ENGINE.apply(
                    conn,
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    event_type="decalcify",
                    payload={
                        "decay_factor": decay,
                        "reason": f"Protocol Ω₃-E Entropic Decay ({fact_type})",
                    },
                    signer="sovereign_decalcifier",
                    commit=False,
                )
            count += 1

        if count > 0:
            await conn.commit()
            logger.info("🧬 [Ω₃-E+] Decalcified %d stagnant facts. Entropy restored.", count)

        return count

    def stop(self) -> None:
        """Halt decalcification."""
        self._is_active = False
        logger.info("🧬 [Ω₃-E] Decalcifier suspended. State freezing.")
