"""Vector L — Prospect Ledger.

Thin wrapper over CORTEX StoreMixin that manages the prospect lifecycle:
DISCOVERED → SCORED → PITCHED → RESPONDED → CONVERTED → CHURNED

Each lifecycle transition is written as an immutable CORTEX Ledger fact
with cryptographic continuity, exergy delta, and hours_saved estimate.

Usage:
    ledger = VectorLLedger(engine)
    prospect_id = await ledger.discover(company="Acme Corp", ...)
    await ledger.pitch(prospect_id, tier=1000)
    await ledger.convert(prospect_id)
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("cortex.agents.vector_l.ledger")


class ProspectStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    SCORED = "SCORED"
    PITCHED = "PITCHED"
    RESPONDED = "RESPONDED"
    CONVERTED = "CONVERTED"
    CHURNED = "CHURNED"
    FILTERED = "FILTERED"  # below exergy threshold


class VectorLLedger:
    """CORTEX Ledger integration for Vector L prospect lifecycle.

    Writes atomic, auditable facts per prospect state transition.
    Uses CORTEX engine if available; falls back to in-memory store.
    """

    FACT_TYPE = "vector_l_prospect"

    def __init__(self, engine: Any | None = None) -> None:
        self._engine = engine
        # Fallback in-memory store when engine is unavailable
        self._store: dict[str, dict] = {}

    # ── Internal helpers ──────────────────────────────────────────

    def _make_fact(
        self,
        prospect_id: str,
        stage: ProspectStage,
        company: str,
        tier: int = 0,
        exergy_gap: float = 0.0,
        evidence: str = "",
        extra: dict | None = None,
    ) -> dict:
        """Build a CORTEX-compatible fact dict."""
        hours_saved = self._estimate_hours_saved(tier)
        return {
            "id": str(uuid4()),
            "type": self.FACT_TYPE,
            "timestamp": time.time(),
            "source": "vector_l_agent",
            "project": "vector_l",
            "summary": f"[Vector L] {company} → {stage.value}",
            "evidence": evidence,
            "impact": f"${tier}/mo potential MRR",
            "next_action": self._next_action(stage),
            "confidence": "C3",
            "exergy_delta": round(1.0 - exergy_gap, 4),
            "exergy_estimate": round(exergy_gap, 4),
            "hours_saved": hours_saved,
            "metadata": {
                "prospect_id": prospect_id,
                "company": company,
                "stage": stage.value,
                "tier_usd": tier,
                "exergy_gap": exergy_gap,
                **(extra or {}),
            },
        }

    @staticmethod
    def _estimate_hours_saved(tier: int) -> float:
        """CHRONOS-1 estimate: tier × ops_factor / 60."""
        # $500/mo → ~8h/mo; $1000/mo → ~20h/mo; $2000/mo → ~40h/mo
        table = {500: 8.0, 1000: 20.0, 2000: 40.0}
        return table.get(tier, 0.0)

    @staticmethod
    def _next_action(stage: ProspectStage) -> str:
        table = {
            ProspectStage.DISCOVERED: "Score prospect and check exergy gap",
            ProspectStage.SCORED: "Compose and send personalized pitch",
            ProspectStage.PITCHED: "Follow up in 72h if no response",
            ProspectStage.RESPONDED: "Schedule demo call or send proposal",
            ProspectStage.CONVERTED: "Onboard customer, deploy CORTEX agent",
            ProspectStage.CHURNED: "Analyze churn signal, update guard",
            ProspectStage.FILTERED: "Archive — below exergy threshold",
        }
        return table.get(stage, "")

    async def _write(self, fact: dict, prospect_id: str) -> None:
        """Persist to CORTEX Ledger or in-memory fallback."""
        if self._engine is not None:
            try:
                # Attempt CORTEX engine write if store method available
                async with self._engine.session() as session:
                    if hasattr(session, "store"):
                        await session.store(fact)
                        return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Ledger write failed, using in-memory: %s", exc)

        # In-memory fallback
        self._store[prospect_id] = fact
        logger.debug(
            "[VectorLLedger] %s → %s (in-memory)",
            prospect_id,
            fact["metadata"]["stage"],
        )

    # ── Lifecycle transitions ─────────────────────────────────────

    async def discover(
        self,
        company: str,
        sources: list[str],
        signals_summary: str = "",
        domain: str | None = None,
    ) -> str:
        """Record a newly discovered company. Returns prospect_id."""
        prospect_id = f"vl_{company[:20].lower().replace(' ', '_')}_{uuid4().hex[:8]}"
        fact = self._make_fact(
            prospect_id=prospect_id,
            stage=ProspectStage.DISCOVERED,
            company=company,
            evidence=signals_summary or f"Signals from: {', '.join(sources)}",
            extra={"domain": domain, "sources": sources},
        )
        await self._write(fact, prospect_id)
        logger.info("[VectorLLedger] DISCOVERED %s → %s", company, prospect_id)
        return prospect_id

    async def score(
        self,
        prospect_id: str,
        company: str,
        exergy_gap: float,
        tier: int,
        evidence: str = "",
    ) -> None:
        """Record scoring result for a prospect."""
        stage = ProspectStage.FILTERED if tier == 0 else ProspectStage.SCORED
        fact = self._make_fact(
            prospect_id=prospect_id,
            stage=stage,
            company=company,
            tier=tier,
            exergy_gap=exergy_gap,
            evidence=evidence or f"Exergy gap: {exergy_gap:.3f} → ${tier}/mo tier",
        )
        await self._write(fact, f"{prospect_id}_scored")
        logger.info(
            "[VectorLLedger] SCORED %s exergy=%.3f tier=$%d",
            company,
            exergy_gap,
            tier,
        )

    async def pitch(
        self,
        prospect_id: str,
        company: str,
        tier: int,
        channel: str = "email",
        pitch_preview: str = "",
    ) -> None:
        """Record a pitch sent to a prospect."""
        fact = self._make_fact(
            prospect_id=prospect_id,
            stage=ProspectStage.PITCHED,
            company=company,
            tier=tier,
            evidence=f"Pitch sent via {channel}. Preview: {pitch_preview[:120]}",
            extra={"channel": channel, "pitched_at": time.time()},
        )
        await self._write(fact, f"{prospect_id}_pitched")
        logger.info("[VectorLLedger] PITCHED %s via %s $%d/mo", company, channel, tier)

    async def respond(
        self,
        prospect_id: str,
        company: str,
        tier: int,
        sentiment: str = "positive",
    ) -> None:
        """Record a prospect response."""
        fact = self._make_fact(
            prospect_id=prospect_id,
            stage=ProspectStage.RESPONDED,
            company=company,
            tier=tier,
            evidence=f"Prospect responded: sentiment={sentiment}",
            extra={"sentiment": sentiment},
        )
        await self._write(fact, f"{prospect_id}_responded")

    async def convert(
        self,
        prospect_id: str,
        company: str,
        tier: int,
        subscription_id: str = "",
    ) -> None:
        """Record a successful conversion (paying customer)."""
        fact = self._make_fact(
            prospect_id=prospect_id,
            stage=ProspectStage.CONVERTED,
            company=company,
            tier=tier,
            exergy_gap=1.0,
            evidence=f"CONVERTED at ${tier}/mo. sub_id={subscription_id}",
            extra={"subscription_id": subscription_id, "mrr_usd": tier},
        )
        await self._write(fact, f"{prospect_id}_converted")
        logger.info(
            "[VectorLLedger] ✅ CONVERTED %s $%d/mo MRR sub=%s",
            company,
            tier,
            subscription_id,
        )

    async def churn(self, prospect_id: str, company: str, tier: int, reason: str = "") -> None:
        """Record a churn event."""
        fact = self._make_fact(
            prospect_id=prospect_id,
            stage=ProspectStage.CHURNED,
            company=company,
            tier=tier,
            evidence=f"Churned. Reason: {reason or 'unknown'}",
        )
        await self._write(fact, f"{prospect_id}_churned")
        logger.warning("[VectorLLedger] CHURNED %s tier=$%d: %s", company, tier, reason)

    # ── Query ─────────────────────────────────────────────────────

    def list_prospects(
        self,
        stage: ProspectStage | None = None,
    ) -> list[dict]:
        """Return in-memory prospects (filtered by stage if provided)."""
        all_facts = list(self._store.values())
        if stage is not None:
            all_facts = [
                f for f in all_facts if f.get("metadata", {}).get("stage") == stage.value
            ]
        return sorted(all_facts, key=lambda f: f.get("timestamp", 0), reverse=True)

    def mrr_total(self) -> int:
        """Sum MRR from converted prospects (in-memory)."""
        return sum(
            f.get("metadata", {}).get("mrr_usd", 0)
            for f in self._store.values()
            if f.get("metadata", {}).get("stage") == ProspectStage.CONVERTED.value
        )
