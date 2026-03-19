"""
PhoenixHandoffAdapter — ΩΩ-HANDOFF Semana 5-6
Gates sovereign agent resurrections on ContinuityVerifier, then retrieves
causal-ordered context from the CORTEX DB to produce a HandoffPayload.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cortex.extensions.swarm.verification import ContinuityVerifier, VerificationResult

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.extensions.swarm.arweave_client import ArweaveClient

logger = logging.getLogger("cortex.extensions.swarm.phoenix_handoff")

__all__ = [
    "HandoffPayload",
    "PhoenixHandoffAdapter",
    "RestorationError",
]

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HandoffPayload:
    """Reconstructed context package for sovereign agent resurrection."""

    fact_id: str
    is_verified: bool
    trust_score: float
    causal_chain: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chain_depth(self) -> int:
        return len(self.causal_chain)


class RestorationError(Exception):
    """Raised when PhoenixProtocol cannot safely restore an agent."""


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class PhoenixHandoffAdapter:
    """Adapts HierarchicalDataRetrieval for the PhoenixProtocol resurrection workflow.

    Workflow:
        1. Verify chain continuity on Arweave (gate).
        2. If verification passes, pull causal chain from DB (ordered by depth).
        3. Return a frozen HandoffPayload for the receiving agent.

    The adapter is intentionally decoupled from the PhoenixOrchestrator —
    it only borrows the causal-retrieval semantics (hierarchical depth ordering),
    not the AST transformation pipeline.
    """

    # Minimum trust threshold to allow restoration
    MIN_TRUST_SCORE: float = 0.5

    def __init__(
        self,
        engine: CortexEngine,
        arweave_client: ArweaveClient | None = None,
        verifier: ContinuityVerifier | None = None,
        max_chain_depth: int = 10,
    ) -> None:
        self._engine = engine
        self._arweave_client = arweave_client
        self._verifier = verifier or ContinuityVerifier()
        self._max_chain_depth = max_chain_depth

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def restore(self, fact_id: str) -> HandoffPayload:
        """Gate + retrieve: verify chain on Arweave, then pull causal context.

        Args:
            fact_id: The Cortex-Fact-Id anchored on Arweave.

        Returns:
            HandoffPayload with verified causal chain.

        Raises:
            RestorationError: If chain is discontinuous or trust too low.
        """
        verification = await self._verify_gate(fact_id)

        causal_chain = await self._fetch_causal_chain(fact_id)

        self._emit_signal(
            "phoenix:restored",
            {
                "fact_id": fact_id,
                "trust_score": verification.trust_score,
                "chain_depth": len(causal_chain),
                "is_continuous": verification.is_continuous,
            },
        )

        return HandoffPayload(
            fact_id=fact_id,
            is_verified=verification.is_continuous,
            trust_score=verification.trust_score,
            causal_chain=causal_chain,
            metadata={
                "verified_txs": verification.verified_txs,
                "gaps": verification.gaps,
                "arweave_chain_length": verification.chain_length,
            },
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _verify_gate(self, fact_id: str) -> VerificationResult:
        """Run ContinuityVerifier and enforce trust threshold."""
        result = await self._verifier.verify(fact_id)

        if not result.is_continuous:
            self._emit_signal(
                "phoenix:restore_failed",
                {
                    "fact_id": fact_id,
                    "reason": "chain_discontinuous",
                    "gaps": result.gaps,
                    "error": result.error,
                },
            )
            raise RestorationError(
                f"Chain discontinuous for {fact_id}: "
                f"{len(result.gaps)} gap(s), error={result.error}"
            )

        if result.trust_score < self.MIN_TRUST_SCORE:
            self._emit_signal(
                "phoenix:restore_failed",
                {
                    "fact_id": fact_id,
                    "reason": "trust_below_threshold",
                    "trust_score": result.trust_score,
                },
            )
            raise RestorationError(
                f"Trust score {result.trust_score:.3f} below threshold "
                f"{self.MIN_TRUST_SCORE} for {fact_id}"
            )

        return result

    async def _fetch_causal_chain(self, fact_id: str) -> list[dict[str, Any]]:
        """Retrieve the causal chain for the fact from the CORTEX DB.

        Falls back to empty list if the engine can't find the fact (e.g. freshly
        bootstrapped agent with no local DB yet).
        """
        try:
            # Resolve fact_id → integer DB id via a lightweight query
            conn = await self._engine.get_conn()
            async with conn.execute(
                "SELECT id FROM facts WHERE content LIKE ? LIMIT 1",
                (f"%{fact_id}%",),
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                logger.debug("PhoenixAdapter: fact_id %s not found in DB, returning []", fact_id)
                return []

            db_id: int = row[0]
            chain = await self._engine.get_causal_chain(
                db_id,
                direction="down",
                max_depth=self._max_chain_depth,
            )
            # Normalise to plain dicts, sorted by causal_depth ascending
            return sorted(
                [
                    {
                        "id": f.get("id"),
                        "type": f.get("fact_type"),
                        "project": f.get("project"),
                        "depth": f.get("causal_depth", 0),
                        "content": f.get("content", ""),
                    }
                    for f in (chain or [])
                ],
                key=lambda x: x.get("depth") or 0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("PhoenixAdapter: causal chain fetch failed: %s", exc)
            return []

    def _emit_signal(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget signal emission. Never raises."""
        try:
            import os

            from cortex.database.core import connect as db_connect
            from cortex.extensions.signals.bus import SignalBus

            db_path = os.environ.get("CORTEX_DB_PATH")
            if not db_path:
                return
            conn = db_connect(db_path, timeout=2)
            try:
                SignalBus(conn).emit(
                    event_type,
                    payload,
                    source="phoenix_handoff_adapter",
                    project="CORTEX_SWARM",
                )
            finally:
                conn.close()
        except Exception:  # noqa: BLE001
            logger.debug("PhoenixAdapter signal emission failed: %s", event_type)
