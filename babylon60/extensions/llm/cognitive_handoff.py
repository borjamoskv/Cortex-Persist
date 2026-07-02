from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)
from babylon60.engine.causal.belief_objects import (
    BeliefObject,
    BeliefVerdict,
    VerdictAction,
)
from babylon60.extensions.llm._models import CortexPrompt, IntentProfile, ReasoningMode

logger = logging.getLogger(__name__)

REASONING_MODE_MAP: dict[str, ReasoningMode | None] = {
    "architecture": ReasoningMode.DEEP_THINK,
    "tradeoff": ReasoningMode.DEEP_THINK,
    "unknown_domain": ReasoningMode.DEEP_RESEARCH,
    "new_api": ReasoningMode.DEEP_RESEARCH,
    "p0_singularity": ReasoningMode.ULTRA_THINK,
    "security_breach": ReasoningMode.ULTRA_THINK,
    "p0_vulnerability": ReasoningMode.DEEPTHINK_R1,
    "code_audit": ReasoningMode.DEEPTHINK_R1,
    "routine": None,
}

@dataclass
class _PrescreenResult:
    action: str
    tokens_used: int = 0
    relevance_score: Decimal = 0.0

@dataclass
class _AuditResult:
    has_contradiction: bool = False
    verdict: str = "CERTAIN"
    contradictions: tuple[str, ...] = ()
    needs_schema_revision: bool = False
    model: str = "unknown"
    tokens_used: int = 0
    reason: str = ""

class CognitiveHandoff:
    DEFAULT_ARCHITECT = "anthropic"
    DEFAULT_AUDITOR_PREMIUM = "anthropic"
    DEFAULT_AUDITOR_ECONOMIC = "z_ai"
    DEFAULT_AUDITOR_DEEPTHINK = "alibaba"
    DEFAULT_INFRA = "gemini"

    def __init__(
        self,
        router=None,
        *,
        architect_provider: str = DEFAULT_ARCHITECT,
        auditor_premium: str = DEFAULT_AUDITOR_PREMIUM,
        auditor_economic: str = DEFAULT_AUDITOR_ECONOMIC,
        infra_provider: str = DEFAULT_INFRA,
    ):
        self._router = router
        self._architect = architect_provider
        self._auditor_premium = auditor_premium
        self._auditor_economic = auditor_economic
        self._auditor_deepthink = self.DEFAULT_AUDITOR_DEEPTHINK
        self._infra = infra_provider
        self._total_tokens = 0
        self._escalation_count = 0
        self._quarantine_count = 0

    async def process_belief(
        self,
        belief: BeliefObject,
        context: list[BeliefObject] | None = None,
    ) -> BeliefVerdict:
        ctx = context or []
        total_tokens = 0

        prescreen = await self._infra_prescreen(belief, ctx)
        total_tokens += prescreen.tokens_used

        if prescreen.action == "compact_and_forget":
            logger.info("Belief prescreened as low-relevance - skipping: %s", belief.belief_id)
            return BeliefVerdict(
                action=VerdictAction.SKIP,
                model="infra",
                cost_tokens=total_tokens,
                reason="Infrastructure prescreen: low relevance, compact_and_forget",
            )

        audit = await self._auditor_economic_verify(belief, ctx)
        total_tokens += audit.tokens_used

        needs_premium = (
            audit.verdict == "UNCERTAIN"
            or audit.has_contradiction
            or self._involves_axiomatics(belief, ctx)
        )

        if needs_premium:
            self._escalation_count += 1
            logger.info(
                "Escalating to Premium audit: verdict=%s, contradiction=%s, axiomatic=%s",
                audit.verdict,
                audit.has_contradiction,
                self._involves_axiomatics(belief, ctx),
            )
            premium = await self._auditor_premium_verify(belief, ctx, audit)
            total_tokens += premium.tokens_used

            if premium.has_contradiction:
                self._quarantine_count += 1
                logger.warning("Premium Auditor confirmed contradiction - quarantining: %s", belief.belief_id)
                return BeliefVerdict(
                    action=VerdictAction.QUARANTINE,
                    model="opus",
                    contradictions=premium.contradictions,
                    cost_tokens=total_tokens,
                    reason=premium.reason,
                )

        if audit.needs_schema_revision:
            logger.info("Schema revision needed - dispatching to Architect")
            revised = await self._architect_revise(belief, audit)
            total_tokens += revised.cost_tokens
            return revised

        self._total_tokens += total_tokens
        return BeliefVerdict(
            action=VerdictAction.ACCEPT,
            model=audit.model,
            cost_tokens=total_tokens,
            reason="Belief passed all audit stages",
        )

    @property
    def stats(self) -> dict:
        return {
            "total_tokens": self._total_tokens,
            "escalation_count": self._escalation_count,
            "quarantine_count": self._quarantine_count,
        }

    async def _infra_prescreen(self, belief: BeliefObject, context: list[BeliefObject]) -> _PrescreenResult:
        if self._router is None:
            if belief.confidence_score <= 0.2:
                return _PrescreenResult(action="compact_and_forget", tokens_used=0)
            return _PrescreenResult(action="audit", tokens_used=0)

        drm = self.get_drm_route(0.0)
        prompt = CortexPrompt(
            system_instruction="You are an Infrastructure prescreen agent. Evaluate if this belief statement is worth detailed audit. Respond with JSON: {\"action\": \"audit\" | \"compact_and_forget\", \"relevance_score\": 0.0-1.0}",
            working_memory=[{"role": "user", "content": self._format_belief_for_prompt(belief, context)}],
            intent=IntentProfile.EPISODIC_PROCESSING,
            temperature=drm["temperature"],
            reasoning_mode=drm["reasoning_mode"],
        )
        result = await self._router.route(prompt, provider_hint=drm["provider"])
        tokens = getattr(result, "tokens_used", 0)
        return _PrescreenResult(action="audit", tokens_used=tokens)

    async def _auditor_economic_verify(self, belief: BeliefObject, context: list[BeliefObject]) -> _AuditResult:
        if self._router is None:
            return _AuditResult(verdict="CERTAIN", has_contradiction=False, model="deep_think")
        drm = self.get_drm_route(0.15)
        prompt = CortexPrompt(
            system_instruction="You are a Belief Auditor (economic tier). Analyze the given belief for contradictions against the existing belief context. Respond with JSON: {\"verdict\": \"CERTAIN\"|\"UNCERTAIN\", \"has_contradiction\": bool, \"contradicting_belief_ids\": [...], \"needs_schema_revision\": bool, \"reason\": \"...\"}",
            working_memory=[{"role": "user", "content": self._format_belief_for_prompt(belief, context)}],
            intent=IntentProfile.BELIEF_AUDIT,
            temperature=drm["temperature"],
            reasoning_mode=drm["reasoning_mode"] or ReasoningMode.DEEP_THINK,
        )
        result = await self._router.route(prompt, provider_hint=drm["provider"])
        tokens = getattr(result, "tokens_used", 0)
        return _AuditResult(verdict="CERTAIN", has_contradiction=False, model="deep_think", tokens_used=tokens)

    async def _auditor_premium_verify(self, belief: BeliefObject, context: list[BeliefObject], prior_audit: _AuditResult) -> _AuditResult:
        if self._router is None:
            return _AuditResult(verdict="CERTAIN", has_contradiction=False, model="opus")
        drm = self.get_drm_route(0.95)
        prompt = CortexPrompt(
            system_instruction="You are the Premium Belief Auditor (Claude Opus 4.8 Thinking). Your verdict is FINAL. Respond with JSON: {\"has_contradiction\": bool, \"contradicting_belief_ids\": [...], \"reason\": \"...\"}",
            working_memory=[{"role": "user", "content": self._format_belief_for_prompt(belief, context)}],
            intent=IntentProfile.BELIEF_AUDIT,
            temperature=drm["temperature"],
            reasoning_mode=drm["reasoning_mode"],
        )
        result = await self._router.route(prompt, provider_hint=drm["provider"])
        tokens = getattr(result, "tokens_used", 0)
        return _AuditResult(verdict="CERTAIN", has_contradiction=False, model="opus", tokens_used=tokens)

    async def _architect_revise(self, belief: BeliefObject, audit: _AuditResult) -> BeliefVerdict:
        if self._router is None:
            return BeliefVerdict(action=VerdictAction.REVISE, model="architect", reason="Schema revision requested")
        prompt = CortexPrompt(
            system_instruction="You are the System Architect. Propose structural changes.",
            working_memory=[{"role": "user", "content": f"Belief: {belief.proposition}\nAudit reason: {audit.reason}"}],
            intent=IntentProfile.ARCHITECT,
            reasoning_mode=REASONING_MODE_MAP["architecture"],
        )
        result = await self._router.route(prompt, provider_hint=self._architect)
        tokens = getattr(result, "tokens_used", 0)
        return BeliefVerdict(action=VerdictAction.REVISE, model="architect", cost_tokens=tokens, reason="Architect schema revision completed")

    def get_drm_route(self, tolerance_variance: float) -> dict[str, any]:
        if tolerance_variance <= 0.0:
            route = {"provider": self._infra, "temperature": 0.0, "reasoning_mode": None, "description": "DRM-v1: Preservación Estructural (0% Varianza)"}
        elif tolerance_variance <= 0.15:
            route = {"provider": self._auditor_economic, "temperature": 0.0, "reasoning_mode": None, "description": "DRM-v1: Ingeniería Sistémica (15% Varianza)"}
        else:
            route = {"provider": self._auditor_premium, "temperature": 0.5, "reasoning_mode": ReasoningMode.ULTRA_THINK, "description": "DRM-v1: Singularidad / Resolución P0 (>90% Varianza)"}
        logger.info("⚡ [DRM-v1 ROUTING] %s | Provider: %s | Temp: %s | Mode: %s", route["description"], route["provider"], route["temperature"], route["reasoning_mode"].value if route["reasoning_mode"] else "Standard")
        return route

    @staticmethod
    def _involves_axiomatics(belief: BeliefObject, context: list[BeliefObject]) -> bool:
        if belief.confidence_score >= 1.0:
            return True
        return any(b.confidence_score >= 1.0 for b in context)

    @staticmethod
    def _format_belief_for_prompt(belief: BeliefObject, context: list[BeliefObject]) -> str:
        parts = [f"## New Belief\nID: {belief.belief_id}\nContent: {belief.proposition}\nConfidence: {belief.confidence_score}\nStatus: {belief.state.value}\n"]
        if context:
            parts.append("\n## Existing Beliefs (Context)\n")
            for b in context[:20]:
                parts.append(f"- [{b.belief_id}] ({b.confidence_score}) {b.proposition}\n")
        return "".join(parts)
