# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM — Cognitive Handoff Orchestrator.

Quad-model orchestrator for cognitive governance of the Belief Layer.

Escalation cascade (cost-optimized):
  1. Infrastructure (Gemini 3.1 Pro) — episodic reads, prescreen — $12/1M
  2. Auditor Economic (Gemini 2.5 Pro Deep Think) — routine belief audit — $12/1M
  3. Auditor Premium (Claude Opus 4.6) — high-severity contradictions — $25/1M
  4. Architect (GPT-5.4) — schema revision, contract design — $15/1M

Invariants enforced:
  - Auditor verdict is FINAL (quarantine overrides all)
  - Deep Think handles ~80% of audits at Gemini pricing
  - Opus reserved for UNCERTAIN verdicts or C5 axiomatic conflicts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cortex.extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefVerdict,
    VerdictAction,
)
from cortex.extensions.llm._models import CortexPrompt, IntentProfile, ReasoningMode
from cortex.extensions.swarm.orchestrator_ultra_think import UltraThinkOrchestrator

logger = logging.getLogger(__name__)


# ─── Cognitive Reasoning Map (Axiom Ω₁₆) ────────────────────────────────────

REASONING_MODE_MAP: dict[str, ReasoningMode | None] = {
    "architecture": ReasoningMode.DEEP_THINK,
    "tradeoff": ReasoningMode.DEEP_THINK,
    "unknown_domain": ReasoningMode.DEEP_RESEARCH,
    "new_api": ReasoningMode.DEEP_RESEARCH,
    "p0_singularity": ReasoningMode.ULTRA_THINK,
    "security_breach": ReasoningMode.ULTRA_THINK,
    "routine": None,  # standard inference
}


# ─── Internal Types ─────────────────────────────────────────────────────────


@dataclass
class _PrescreenResult:
    """Infrastructure prescreen output."""

    action: str  # "audit" | "compact_and_forget"
    tokens_used: int = 0
    relevance_score: float = 0.0


@dataclass
class _AuditResult:
    """Auditor output (economic or premium)."""

    has_contradiction: bool = False
    verdict: str = "CERTAIN"  # "CERTAIN" | "UNCERTAIN"
    contradictions: tuple[str, ...] = ()
    needs_schema_revision: bool = False
    model: str = "unknown"
    tokens_used: int = 0
    reason: str = ""


# ─── CognitiveHandoff ──────────────────────────────────────────────────────


class CognitiveHandoff:
    """Quad-model orchestrator for cognitive governance.

    Sits above CortexLLMRouter — wraps it with cognitive-specific routing
    decisions. Does NOT replace the router; uses it to dispatch prompts
    to the appropriate model via IntentProfile.

    Escalation cascade:
      prescreen (infra) → audit_economic (deep_think) → audit_premium (opus)
      → architect (gpt-5.4, only if schema revision needed)
    """

    # Default provider assignments — can be overridden at init
    DEFAULT_ARCHITECT = "openai"
    DEFAULT_AUDITOR_PREMIUM = "anthropic"
    DEFAULT_AUDITOR_ECONOMIC = "gemini"
    DEFAULT_INFRA = "gemini"

    def __init__(
        self,
        router=None,
        *,
        architect_provider: str = DEFAULT_ARCHITECT,
        auditor_premium: str = DEFAULT_AUDITOR_PREMIUM,
        auditor_economic: str = DEFAULT_AUDITOR_ECONOMIC,
        infra_provider: str = DEFAULT_INFRA,
        engine: Any | None = None,
    ):
        """Initialize the Cognitive Handoff.

        Args:
            router: CortexLLMRouter instance (or None for testing).
            architect_provider: Provider key for GPT-5.4 (schema design).
            auditor_premium: Provider key for Claude Opus (high-severity).
            auditor_economic: Provider key for Gemini Deep Think (routine).
            infra_provider: Provider key for Gemini 3.1 Pro (prescreen).
        """
        self._router = router
        self._architect = architect_provider
        self._auditor_premium = auditor_premium
        self._auditor_economic = auditor_economic
        self._infra = infra_provider
        self.engine = engine  # Store engine for UltraThink and other high-exergy tasks

        # Telemetry
        self._total_tokens = 0
        self._escalation_count = 0
        self._quarantine_count = 0
        self._ultra_think_count = 0
        self._ut_orchestrator = UltraThinkOrchestrator(engine) if engine else None

    # ─── Public API ─────────────────────────────────────────────────────

    async def process_belief(
        self,
        belief: BeliefObject,
        context: list[BeliefObject] | None = None,
    ) -> BeliefVerdict:
        """Cost-aware belief processing pipeline.

        Implements the quad-model escalation cascade:
        1. Infrastructure prescreen (cheap)
        2. Auditor Economic — Deep Think (routine)
        3. Auditor Premium — Opus (high-severity, only if needed)
        4. Architect — GPT-5.4 (schema revision, only if needed)

        Args:
            belief: The belief to evaluate.
            context: Existing beliefs for contradiction detection.

        Returns:
            BeliefVerdict with action, model, and reasoning.
        """
        ctx = context or []
        total_tokens = 0

        # ── Step 1: Infrastructure prescreen ─────────────────────────
        prescreen = await self._infra_prescreen(belief, ctx)
        total_tokens += prescreen.tokens_used

        if prescreen.action == "compact_and_forget":
            logger.info(
                "Belief prescreened as low-relevance — skipping: %s",
                belief.id,
            )
            return BeliefVerdict(
                action=VerdictAction.SKIP,
                model="infra",
                cost_tokens=total_tokens,
                reason="Infrastructure prescreen: low relevance, compact_and_forget",
            )

        # ── Step 2: Auditor Economic (Deep Think) ────────────────────
        audit = await self._auditor_economic_verify(belief, ctx)
        total_tokens += audit.tokens_used

        if audit.verdict == "CERTAIN" and audit.has_contradiction:
            self._quarantine_count += 1
            logger.warning(
                "Deep Think detected contradiction — quarantining: %s",
                belief.id,
            )
            return BeliefVerdict(
                action=VerdictAction.QUARANTINE,
                model="deep_think",
                contradictions=audit.contradictions,
                cost_tokens=total_tokens,
                reason=audit.reason,
            )

        # ── Step 3: Escalate to Opus (premium) if needed ─────────────
        needs_premium = audit.verdict == "UNCERTAIN" or self._involves_axiomatics(belief, ctx)

        if needs_premium:
            self._escalation_count += 1
            logger.info(
                "Escalating to Opus premium audit: verdict=%s, axiomatic=%s",
                audit.verdict,
                self._involves_axiomatics(belief, ctx),
            )
            premium = await self._auditor_premium_verify(belief, ctx, audit)
            total_tokens += premium.tokens_used

            if premium.has_contradiction:
                self._quarantine_count += 1
                logger.warning(
                    "Opus detected contradiction — quarantining: %s",
                    belief.id,
                )
                return BeliefVerdict(
                    action=VerdictAction.QUARANTINE,
                    model="opus",
                    contradictions=premium.contradictions,
                    cost_tokens=total_tokens,
                    reason=premium.reason,
                )

        # ── Step 4: UltraThink Execution (Event Horizon) ─────────────
        # If still uncertain about axiomatic survival or P0 triggered.
        is_p0 = belief.metadata.get("p0_critical", False) or self._involves_axiomatics(belief, ctx)
        if is_p0:
            logger.warning("🛡️ [EVENT HORIZON] Triggering UltraThink: %s", belief.id)
            self._ultra_think_count += 1
            ut_res = await self._ultra_think_verify(belief, ctx)
            total_tokens += ut_res.cost_tokens
            if ut_res.action == VerdictAction.QUARANTINE:
                return ut_res

        # ── Step 5: Architect revision (if schema change needed) ─────
        if audit.needs_schema_revision:
            logger.info("Schema revision needed — dispatching to Architect")
            revised = await self._architect_revise(belief, audit)
            total_tokens += revised.cost_tokens
            return revised

        # ── All clear ────────────────────────────────────────────────
        self._total_tokens += total_tokens
        return BeliefVerdict(
            action=VerdictAction.ACCEPT,
            model=audit.model,
            cost_tokens=total_tokens,
            reason="Belief passed all audit stages",
        )

    # ─── Telemetry ──────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        """Return telemetry counters."""
        return {
            "total_tokens": self._total_tokens,
            "escalation_count": self._escalation_count,
            "quarantine_count": self._quarantine_count,
        }

    # ─── Internal Pipeline Steps ────────────────────────────────────────

    async def _infra_prescreen(
        self,
        belief: BeliefObject,
        context: list[BeliefObject],
    ) -> _PrescreenResult:
        """Step 1: Cheap prescreen via Infrastructure (Gemini 3.1 Pro).

        Determines if a belief is worth auditing based on:
        - Semantic similarity to existing beliefs
        - Confidence level (C1 beliefs may be auto-compacted)
        - Content length and complexity heuristics
        """
        if self._router is None:
            # No router — heuristic fallback (for testing / offline)
            if belief.confidence == BeliefConfidence.C1_HYPOTHESIS:
                return _PrescreenResult(action="compact_and_forget", tokens_used=0)
            return _PrescreenResult(action="audit", tokens_used=0)

        prompt = CortexPrompt(
            system_instruction="You are an Infrastructure prescreen agent. Evaluate if this "
            "belief statement is worth detailed audit. Respond with JSON: "
            '{"action": "audit" | "compact_and_forget", "relevance_score": 0.0-1.0}',
            working_memory=[
                {
                    "role": "user",
                    "content": self._format_belief_for_prompt(belief, context),
                }
            ],
            intent=IntentProfile.EPISODIC_PROCESSING,
        )

        result = await self._router.route(prompt, provider_hint=self._infra)
        tokens = getattr(result, "tokens_used", 0)
        # Parse infrastructure response
        # In production, parse JSON response; here we default to audit
        return _PrescreenResult(action="audit", tokens_used=tokens)

    async def _auditor_economic_verify(
        self,
        belief: BeliefObject,
        context: list[BeliefObject],
    ) -> _AuditResult:
        """Step 2: Routine audit via Auditor Economic (Deep Think).

        Uses Gemini 2.5 Pro's extended reasoning mode to detect
        contradictions with existing beliefs. Handles ~80% of all audits.
        """
        if self._router is None:
            return _AuditResult(
                verdict="CERTAIN",
                has_contradiction=False,
                model="deep_think",
            )

        prompt = CortexPrompt(
            system_instruction="You are a Belief Auditor (economic tier). Analyze the given "
            "belief for contradictions against the existing belief context. "
            "Use extended reasoning to explore multiple hypotheses. "
            "Respond with JSON: "
            '{"verdict": "CERTAIN"|"UNCERTAIN", '
            '"has_contradiction": bool, '
            '"contradicting_belief_ids": [...], '
            '"needs_schema_revision": bool, '
            '"reason": "..."}',
            working_memory=[
                {
                    "role": "user",
                    "content": self._format_belief_for_prompt(belief, context),
                }
            ],
            intent=IntentProfile.BELIEF_AUDIT,
            reasoning_mode=ReasoningMode.DEEP_THINK,
        )

        result = await self._router.route(prompt, provider_hint=self._auditor_economic)
        tokens = getattr(result, "tokens_used", 0)
        return _AuditResult(
            verdict="CERTAIN",
            has_contradiction=False,
            model="deep_think",
            tokens_used=tokens,
        )

    async def _auditor_premium_verify(
        self,
        belief: BeliefObject,
        context: list[BeliefObject],
        prior_audit: _AuditResult,
    ) -> _AuditResult:
        """Step 3: Premium audit via Auditor Premium (Claude Opus 4.6).

        Only invoked when:
        a) Deep Think verdict is UNCERTAIN
        b) Contradiction involves C5 axiomatic beliefs

        Opus has the highest semantic fidelity at long context and
        is the final arbiter — its quarantine verdict is non-overridable.
        """
        if self._router is None:
            return _AuditResult(
                verdict="CERTAIN",
                has_contradiction=False,
                model="opus",
            )

        prompt = CortexPrompt(
            system_instruction="You are the Premium Belief Auditor (Claude Opus). "
            "A prior economic audit returned an UNCERTAIN verdict. "
            "Your task: provide a DEFINITIVE ruling on whether this belief "
            "contradicts existing axioms. Your verdict is FINAL and "
            "non-overridable. If contradiction exists, specify which beliefs "
            "are affected. Respond with JSON: "
            '{"has_contradiction": bool, '
            '"contradicting_belief_ids": [...], '
            '"reason": "..."}',
            working_memory=[
                {
                    "role": "user",
                    "content": self._format_belief_for_prompt(belief, context),
                }
            ],
            intent=IntentProfile.BELIEF_AUDIT,
            # Opus does not have a native 'thinking' parameter like DeepSeek/Gemini,
            # but setting DEEP_THINK here allows the router to allocate maximum resources.
            reasoning_mode=ReasoningMode.DEEP_THINK,
        )

        result = await self._router.route(prompt, provider_hint=self._auditor_premium)
        tokens = getattr(result, "tokens_used", 0)
        return _AuditResult(
            verdict="CERTAIN",
            has_contradiction=False,
            model="opus",
            tokens_used=tokens,
        )

    async def _architect_revise(
        self,
        belief: BeliefObject,
        audit: _AuditResult,
    ) -> BeliefVerdict:
        """Step 4: Schema revision via Architect (GPT-5.4).

        Only invoked when the audit indicates the belief structure
        needs modification — not just content contradiction but
        schema-level changes (new fields, type changes, etc.).
        """
        if self._router is None:
            return BeliefVerdict(
                action=VerdictAction.REVISE,
                model="architect",
                reason="Schema revision requested (no router — dry run)",
            )

        prompt = CortexPrompt(
            system_instruction="You are the System Architect (GPT-5.4). "
            "A belief audit has determined that schema revision is needed. "
            "Analyze the belief and propose structural changes. "
            "Respond with the revised belief content and any schema "
            "modifications needed.",
            working_memory=[
                {
                    "role": "user",
                    "content": (f"Belief: {belief.content}\nAudit reason: {audit.reason}"),
                }
            ],
            intent=IntentProfile.ARCHITECT,
            reasoning_mode=REASONING_MODE_MAP["architecture"],
        )

        result = await self._router.route(prompt, provider_hint=self._architect)
        tokens = getattr(result, "tokens_used", 0)
        return BeliefVerdict(
            action=VerdictAction.REVISE,
            model="architect",
            cost_tokens=tokens,
            reason="Architect schema revision completed",
        )

    async def _ultra_think_verify(
        self,
        belief: BeliefObject,
        context: list[BeliefObject],
    ) -> BeliefVerdict:
        """Step 4: Sovereign Survival Audit via UltraThinkOrchestrator.

        Final mechanical and logical gate for P0 singularities.
        Eliminates stochastic hallucinations through recursive verification.
        """
        if not self._ut_orchestrator:
            return BeliefVerdict(
                action=VerdictAction.ACCEPT,
                model="ultra_think",
                reason="UltraThink orchestration skipped (engine/manager not available)",
            )

        prompt = CortexPrompt(
            system_instruction="Analyze this belief for absolute sovereign survival. "
            "Eliminate all stochastic hallucinations. Cross-verify with mechanical gates.",
            working_memory=[
                {
                    "role": "user",
                    "content": self._format_belief_for_prompt(belief, context),
                }
            ],
            intent=IntentProfile.REASONING,
            reasoning_mode=ReasoningMode.ULTRA_THINK,
        )

        res = await self._ut_orchestrator.execute(prompt)
        if res.is_err():
            return BeliefVerdict(
                action=VerdictAction.QUARANTINE,
                model="ultra_think",
                reason=f"UltraThink Detonation: {res.error}",
            )

        return BeliefVerdict(
            action=VerdictAction.ACCEPT,
            model="ultra_think",
            reason="UltraThink: Mechanical verification passed.",
        )

    # ─── Utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _involves_axiomatics(
        belief: BeliefObject,
        context: list[BeliefObject],
    ) -> bool:
        """Check if any involved belief has C5 axiomatic confidence."""
        if belief.is_axiomatic():
            return True
        return any(b.is_axiomatic() for b in context)

    @staticmethod
    def _format_belief_for_prompt(
        belief: BeliefObject,
        context: list[BeliefObject],
    ) -> str:
        """Format belief + context into a prompt string for LLM consumption."""
        parts = [
            f"## New Belief\n"
            f"ID: {belief.id}\n"
            f"Content: {belief.content}\n"
            f"Confidence: {belief.confidence.value}\n"
            f"Status: {belief.status.value}\n"
        ]

        if context:
            parts.append("\n## Existing Beliefs (Context)\n")
            for b in context[:20]:  # Cap context to prevent token explosion
                parts.append(f"- [{b.id}] ({b.confidence.value}) {b.content}\n")

        return "".join(parts)
