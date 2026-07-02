# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Hypervisor - Belief Engine.

Cognitive governance layer that connects the CognitiveHandoff orchestrator
to the AgencyHypervisor pipeline. Sits between remember() and the database,
intercepting new facts to check for belief contradictions.

Implements Invariant 2: Auditor quarantine overrides all execution.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from babylon60.engine.causal.belief_objects import (
    BeliefObject,
    BeliefRelations,
    BeliefState,
    BeliefVerdict,
    ProvenanceEnvelope,
    VerdictAction,
)

if TYPE_CHECKING:
    from babylon60.extensions.llm.cognitive_handoff import CognitiveHandoff

logger = logging.getLogger(__name__)


def _uuid7() -> str:
    """Generate a UUID v7 (time-sortable) as string."""
    ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex
    return f"{ts}-{uid[:16]}"


def _now_iso() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()


class BeliefEngine:
    """Cognitive governance layer for the Hypervisor.

    Evaluates incoming content against existing beliefs using the
    CognitiveHandoff quad-model cascade. If a contradiction is
    detected, the belief is quarantined (CONTESTED).
    """

    def __init__(
        self,
        cortex_engine=None,
        handoff: CognitiveHandoff | None = None,
        *,
        max_context_beliefs: int = 50,
    ):
        self._engine = cortex_engine
        self._handoff = handoff
        self._max_context = max_context_beliefs
        self._cache: dict[str, list[BeliefObject]] = {}

    async def evaluate_incoming(
        self,
        content: str,
        project: str,
        tenant_id: str = "default",
        confidence: float = 0.5,
        source: str | None = None,
    ) -> BeliefVerdict:
        """Evaluate incoming content for belief contradictions."""
        # Build candidate belief
        agent_id = source.split(":")[-1] if source and "agent:" in source else "unknown"
        
        provenance = ProvenanceEnvelope(
            source_hash="0" * 64, # Placeholder for cryptographic hash
            source_type="agent" if source and "agent:" in source else "human",
            tenant_id=tenant_id,
            signer_id=agent_id,
            signature="cortex-taint-placeholder",
            created_at=_now_iso(),
            was_generated_by=source or "unknown",
        )

        candidate = BeliefObject(
            belief_id=_uuid7(),
            proposition=content,
            semantic_embedding=[0.0] * 1536, # Placeholder vector
            state=BeliefState.ACTIVE,
            confidence_score=confidence,
            variance=0.1,
            decay_rate=0.01,
            provenance=provenance,
            relations=BeliefRelations(entails=[], discards=[])
        )

        context = await self._load_context(project, tenant_id)

        if self._handoff is None:
            logger.warning("No CognitiveHandoff configured - auto-accepting belief")
            return BeliefVerdict(
                action=VerdictAction.ACCEPT,
                model="none",
                reason="No handoff configured - passthrough mode",
            )

        verdict = await self._handoff.process_belief(candidate, context)

        if verdict.action == VerdictAction.QUARANTINE:
            await self._quarantine_belief(candidate, verdict)

            # Epistemic Slashing (Axiom Ω₃)
            if verdict.model in ("opus", "fable", "architect", "o1-preview", "o1-mini"):
                try:
                    from babylon60.engine.forensic.slashing import SlashingEngine, SlashingPenalty
                    conn = getattr(self._engine, "conn", None) or getattr(self._engine, "_conn", None)
                    if conn:
                        logger.error("⚔️ [Ω₃] EPISTEMIC SLASHING: %s quarantined by %s", agent_id, verdict.model)
                        await SlashingEngine.slash(
                            conn=conn,
                            agent_id=agent_id,
                            penalty_type=SlashingPenalty.CRYPTOGRAPHIC_TAINT,
                            reason=f"Hallucination/Contradiction caught by {verdict.model}: {verdict.reason}",
                            tenant_id=candidate.provenance.tenant_id,
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.error("Failed to execute Epistemic Slashing: %s", exc)

        elif verdict.action == VerdictAction.ACCEPT:
            await self._persist_belief(candidate)

        return verdict

    async def quarantine(self, belief_id: str, reason: str) -> None:
        """Manually quarantine a belief by ID."""
        logger.warning("Manual quarantine: %s - %s", belief_id, reason)
        if self._engine is not None:
            await self._engine.store(
                content=f"[QUARANTINE] Belief {belief_id}: {reason}",
                fact_type="decision",
                project="cortex-internal",
                source="belief_engine",
                meta={"belief_id": belief_id, "action": "quarantine"},
                confidence="C4",
            )

    async def get_belief_graph(
        self,
        project: str,
        tenant_id: str = "default",
    ) -> list[BeliefObject]:
        """Retrieve all active beliefs for a project."""
        return await self._load_context(project, tenant_id)

    async def _load_context(
        self,
        project: str,
        tenant_id: str,
    ) -> list[BeliefObject]:
        """Load existing beliefs as context for auditing."""
        cache_key = f"{tenant_id}:{project}"
        if cache_key in self._cache:
            return self._cache[cache_key][: self._max_context]

        if self._engine is None:
            return []

        try:
            facts = await self._engine.recall(
                project=project,
                limit=self._max_context,
                tenant_id=tenant_id,
                fact_type="belief",
            )
            beliefs = []
            for fact in facts:
                meta = fact.meta if isinstance(fact.meta, dict) else {}
                belief_data = meta.get("belief_object")
                if belief_data and isinstance(belief_data, dict):
                    beliefs.append(BeliefObject.model_validate(belief_data))
            self._cache[cache_key] = beliefs
            return beliefs[: self._max_context]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load belief context: %s", exc)
            return []

    async def _quarantine_belief(
        self,
        belief: BeliefObject,
        verdict: BeliefVerdict,
    ) -> None:
        """Persist a quarantined belief to the engine."""
        quarantined = belief.model_copy(update={
            "state": BeliefState.CONTESTED,
            "relations": BeliefRelations(entails=belief.relations.entails, discards=list(verdict.contradictions))
        })

        if self._engine is not None:
            await self._engine.store(
                content=quarantined.proposition,
                fact_type="belief",
                project="cortex-internal",
                source=f"belief_engine:{verdict.model}",
                meta={
                    "belief_object": quarantined.model_dump(mode="json"),
                    "verdict_action": verdict.action.value,
                    "verdict_reason": verdict.reason,
                },
                confidence=quarantined.confidence_score,
            )

        cache_key = f"{quarantined.provenance.tenant_id}:cortex-internal"
        self._cache.pop(cache_key, None)

        if verdict.model != "system_cascade":
            await self._cascade_quarantine(
                root_id=quarantined.belief_id,
                project="cortex-internal",
                tenant_id=quarantined.provenance.tenant_id,
                reason=verdict.reason,
            )

    async def _cascade_quarantine(
        self,
        root_id: str,
        project: str,
        tenant_id: str,
        reason: str,
    ) -> None:
        """Recursively quarantine any active beliefs that depend on the root_id."""
        if self._engine is None:
            return

        try:
            facts = await self._engine.recall(
                project=project,
                limit=None,
                tenant_id=tenant_id,
                fact_type="belief",
            )
            context = []
            for fact in facts:
                meta = fact.meta if hasattr(fact, "meta") else fact.get("meta", {})
                belief_data = meta.get("belief_object")
                if belief_data:
                    context.append(BeliefObject.model_validate(belief_data))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load unbounded context for cascade: %s", exc)
            return

        for b in context:
            if b.state == BeliefState.ACTIVE and root_id in b.relations.entails:
                logger.warning(
                    "⛓️ [CASCADING QUARANTINE] Orphaning dependent belief %s (depends on %s)",
                    b.belief_id,
                    root_id,
                )
                cascade_verdict = BeliefVerdict(
                    action=VerdictAction.QUARANTINE,
                    model="system_cascade",
                    reason=f"Cascading Quarantine: Dependent root belief {root_id} collapsed. Root cause: {reason}",
                )
                await self._quarantine_belief(b, cascade_verdict)
                await self._cascade_quarantine(b.belief_id, project, tenant_id, reason)

    async def _persist_belief(self, belief: BeliefObject) -> None:
        """Persist an accepted belief to the engine."""
        if self._engine is not None:
            await self._engine.store(
                content=belief.proposition,
                fact_type="belief",
                project="cortex-internal",
                source="belief_engine",
                meta={"belief_object": belief.model_dump(mode="json")},
                confidence=belief.confidence_score,
            )

        cache_key = f"{belief.provenance.tenant_id}:cortex-internal"
        if cache_key not in self._cache:
            self._cache[cache_key] = []
        self._cache[cache_key].append(belief)
