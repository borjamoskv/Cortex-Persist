# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Hypervisor — Belief Engine.

Cognitive governance layer that connects the CognitiveHandoff orchestrator
to the AgencyHypervisor pipeline. Sits between remember() and the database,
intercepting new facts to check for belief contradictions.

Implements Invariant 2: Auditor quarantine overrides all execution.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, Optional

from cortex.extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
    BeliefVerdict,
    ProvenanceChain,
    ProvenanceEntry,
    VerdictAction,
)

if TYPE_CHECKING:
    from cortex.extensions.llm.cognitive_handoff import CognitiveHandoff

logger = logging.getLogger(__name__)


class BeliefEngine:
    """Cognitive governance layer for the Hypervisor.

    Evaluates incoming content against existing beliefs using the
    CognitiveHandoff quad-model cascade. If a contradiction is
    detected, the belief is quarantined — this verdict is final
    and cannot be overridden by downstream components.

    Usage::

        engine = BeliefEngine(cortex_engine, cognitive_handoff)
        verdict = await engine.evaluate_incoming(
            content="The launch date is Q3 2026",
            project="my-project",
        )
        if verdict.action == VerdictAction.QUARANTINE:
            # Handle contradiction
            ...
    """

    def __init__(
        self,
        cortex_engine=None,
        handoff: Optional[CognitiveHandoff] = None,
        *,
        max_context_beliefs: int = 50,
    ):
        """Initialize the Belief Engine.

        Args:
            cortex_engine: CortexEngine instance for fact storage/retrieval.
            handoff: CognitiveHandoff instance for quad-model auditing.
            max_context_beliefs: Max beliefs to load as audit context.
        """
        self._engine = cortex_engine
        self._handoff = handoff
        self._max_context = max_context_beliefs

        # In-memory belief cache (project → beliefs)
        self._cache: dict[str, list[BeliefObject]] = {}

    # ─── Public API ─────────────────────────────────────────────────────

    async def evaluate_incoming(
        self,
        content: str,
        project: str,
        tenant_id: str = "default",
        confidence: BeliefConfidence = BeliefConfidence.C2_TENTATIVE,
        source: Optional[str] = None,
    ) -> BeliefVerdict:
        """Evaluate incoming content for belief contradictions.

        Creates a candidate BeliefObject, loads existing beliefs as
        context, and routes through the CognitiveHandoff cascade.

        Args:
            content: The belief statement to evaluate.
            project: Project namespace.
            tenant_id: Multi-tenant isolation key.
            confidence: Initial confidence level.
            source: Origin of this belief (e.g., "agent:gemini").

        Returns:
            BeliefVerdict with action and reasoning.
        """
        # Build candidate belief
        from cortex.extensions.hypervisor.belief_object import _now_iso

        provenance = ProvenanceChain()
        if source:
            provenance = provenance.extend(
                ProvenanceEntry(
                    source_type="model_inference" if "agent:" in source else "external",
                    source_id=source,
                    model=source.split(":")[-1] if "agent:" in source else None,
                    timestamp=_now_iso(),
                    action="created",
                )
            )

        candidate = BeliefObject(
            content=content,
            project=project,
            tenant_id=tenant_id,
            confidence=confidence,
            provenance=provenance,
        )

        # Load existing beliefs as context
        context = await self._load_context(project, tenant_id)

        # Route through CognitiveHandoff
        if self._handoff is None:
            logger.warning("No CognitiveHandoff configured — auto-accepting belief")
            return BeliefVerdict(
                action=VerdictAction.ACCEPT,
                model="none",
                reason="No handoff configured — passthrough mode",
            )

        verdict = await self._handoff.process_belief(candidate, context)

        # Handle quarantine — persist the quarantine state
        if verdict.action == VerdictAction.QUARANTINE:
            await self._quarantine_belief(candidate, verdict)

        # Handle accept — persist the belief
        elif verdict.action == VerdictAction.ACCEPT:
            await self._persist_belief(candidate)

        return verdict

    async def quarantine(self, belief_id: str, reason: str) -> None:
        """Manually quarantine a belief by ID.

        Args:
            belief_id: The belief ID to quarantine.
            reason: Human-readable reason for quarantine.
        """
        logger.warning("Manual quarantine: %s — %s", belief_id, reason)

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
        """Retrieve all active beliefs for a project.

        Args:
            project: Project namespace.
            tenant_id: Multi-tenant isolation key.

        Returns:
            List of active BeliefObjects.
        """
        return await self._load_context(project, tenant_id)

    # ─── Internal ───────────────────────────────────────────────────────

    async def _load_context(
        self,
        project: str,
        tenant_id: str,
    ) -> list[BeliefObject]:
        """Load existing beliefs as context for auditing.

        First checks in-memory cache, then falls back to CortexEngine
        fact retrieval (filtering for fact_type='belief').
        """
        cache_key = f"{tenant_id}:{project}"

        if cache_key in self._cache:
            return self._cache[cache_key][: self._max_context]

        if self._engine is None:
            return []

        # Query existing beliefs from the engine
        try:
            facts = await self._engine.recall(
                query=f"project:{project} type:belief",
                project=project,
                limit=self._max_context,
            )

            beliefs = []
            for fact in facts:
                try:
                    meta = fact.meta if isinstance(fact.meta, dict) else {}
                    belief_data = meta.get("belief_object")
                    if belief_data and isinstance(belief_data, dict):
                        beliefs.append(BeliefObject.from_dict(belief_data))
                    else:
                        conf_val = str(fact.confidence)
                        valid_confs = {c.value for c in BeliefConfidence}
                        beliefs.append(
                            BeliefObject(
                                content=fact.content,
                                project=project,
                                tenant_id=tenant_id,
                                confidence=BeliefConfidence(conf_val)
                                if conf_val in valid_confs
                                else BeliefConfidence.C2_TENTATIVE,
                            )
                        )
                except (KeyError, ValueError, TypeError) as exc:
                    logger.debug("Skipping malformed belief fact: %s", exc)

            self._cache[cache_key] = beliefs
            return beliefs[: self._max_context]

        except Exception as exc:
            logger.warning("Failed to load belief context: %s", exc)
            return []

    async def _quarantine_belief(
        self,
        belief: BeliefObject,
        verdict: BeliefVerdict,
    ) -> None:
        """Persist a quarantined belief to the engine."""
        quarantined = replace(
            belief,
            status=BeliefStatus.QUARANTINED,
            contradicts=verdict.contradictions,
            arbitrated_by=verdict.model,
        )

        if self._engine is not None:
            await self._engine.store(
                content=quarantined.content,
                fact_type="belief",
                project=quarantined.project,
                source=f"belief_engine:{verdict.model}",
                meta={
                    "belief_object": quarantined.to_dict(),
                    "verdict_action": verdict.action.value,
                    "verdict_reason": verdict.reason,
                },
                confidence=quarantined.confidence.value,
            )

        # Invalidate cache
        cache_key = f"{quarantined.tenant_id}:{quarantined.project}"
        self._cache.pop(cache_key, None)

    async def _persist_belief(self, belief: BeliefObject) -> None:
        """Persist an accepted belief to the engine."""
        if self._engine is not None:
            await self._engine.store(
                content=belief.content,
                fact_type="belief",
                project=belief.project,
                source="belief_engine",
                meta={"belief_object": belief.to_dict()},
                confidence=belief.confidence.value,
            )

        # Update cache
        cache_key = f"{belief.tenant_id}:{belief.project}"
        if cache_key not in self._cache:
            self._cache[cache_key] = []
        self._cache[cache_key].append(belief)
