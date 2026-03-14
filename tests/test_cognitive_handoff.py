# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Tests for CognitiveHandoff — quad-model escalation cascade."""

from __future__ import annotations

import pytest

from cortex.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
    BeliefVerdict,
    VerdictAction,
)
from cortex.llm._models import IntentProfile
from cortex.llm.cognitive_handoff import CognitiveHandoff


# ─── IntentProfile Extensions ───────────────────────────────────────────────


class TestCognitiveIntents:
    def test_belief_audit_exists(self):
        assert IntentProfile.BELIEF_AUDIT.value == "belief_audit"

    def test_episodic_processing_exists(self):
        assert IntentProfile.EPISODIC_PROCESSING.value == "episodic_processing"

    def test_original_intents_preserved(self):
        """Regression: new intents must not break existing ones."""
        assert IntentProfile.CODE.value == "code"
        assert IntentProfile.REASONING.value == "reasoning"
        assert IntentProfile.CREATIVE.value == "creative"
        assert IntentProfile.ARCHITECT.value == "architect"
        assert IntentProfile.GENERAL.value == "general"


# ─── CognitiveHandoff (No Router — Heuristic Mode) ─────────────────────────


class TestCognitiveHandoffNoRouter:
    """Test CognitiveHandoff without a router (offline/testing mode)."""

    def _make_handoff(self) -> CognitiveHandoff:
        return CognitiveHandoff(router=None)

    @pytest.mark.asyncio
    async def test_c1_belief_skipped(self):
        """C1 hypothesis beliefs should be auto-skipped by prescreen."""
        handoff = self._make_handoff()
        belief = BeliefObject(
            content="Maybe the sky is green",
            project="test",
            confidence=BeliefConfidence.C1_HYPOTHESIS,
        )
        verdict = await handoff.process_belief(belief)
        assert verdict.action == VerdictAction.SKIP

    @pytest.mark.asyncio
    async def test_c2_belief_accepted(self):
        """C2+ beliefs should pass through audit in no-router mode."""
        handoff = self._make_handoff()
        belief = BeliefObject(
            content="SQLite is suitable for local persistence",
            project="cortex",
            confidence=BeliefConfidence.C2_TENTATIVE,
        )
        verdict = await handoff.process_belief(belief)
        assert verdict.action == VerdictAction.ACCEPT

    @pytest.mark.asyncio
    async def test_axiomatic_context_no_escalation_without_router(self):
        """Without router, axiomatic context doesn't trigger real Opus call."""
        handoff = self._make_handoff()
        belief = BeliefObject(
            content="New claim about entropy",
            project="physics",
            confidence=BeliefConfidence.C3_PROBABLE,
        )
        axiomatic_ctx = BeliefObject(
            content="Entropy always increases",
            project="physics",
            confidence=BeliefConfidence.C5_AXIOMATIC,
        )
        verdict = await handoff.process_belief(belief, [axiomatic_ctx])
        # Without router, escalation to Opus returns ACCEPT (no real LLM)
        assert verdict.action == VerdictAction.ACCEPT

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Telemetry counters should track escalations and quarantines."""
        handoff = self._make_handoff()
        assert handoff.stats["total_tokens"] == 0
        assert handoff.stats["escalation_count"] == 0
        assert handoff.stats["quarantine_count"] == 0


# ─── CognitiveHandoff Invariants ────────────────────────────────────────────


class TestCognitiveHandoffInvariants:
    """Test the three core invariants of the Cognitive Handoff."""

    def test_involves_axiomatics_true(self):
        """Invariant check: C5 beliefs trigger premium escalation."""
        axiomatic = BeliefObject(
            content="Fundamental truth",
            project="test",
            confidence=BeliefConfidence.C5_AXIOMATIC,
        )
        normal = BeliefObject(
            content="Regular claim",
            project="test",
            confidence=BeliefConfidence.C3_PROBABLE,
        )
        assert CognitiveHandoff._involves_axiomatics(normal, [axiomatic]) is True

    def test_involves_axiomatics_false(self):
        """No C5 beliefs → no premium escalation."""
        beliefs = [
            BeliefObject(content=f"b-{i}", project="test")
            for i in range(3)
        ]
        candidate = BeliefObject(content="candidate", project="test")
        assert CognitiveHandoff._involves_axiomatics(candidate, beliefs) is False

    def test_format_belief_for_prompt(self):
        """Prompt formatting should include belief content and context."""
        belief = BeliefObject(
            content="The API uses gRPC",
            project="cortex",
            confidence=BeliefConfidence.C3_PROBABLE,
        )
        context = [
            BeliefObject(
                content="The API uses REST",
                project="cortex",
                confidence=BeliefConfidence.C4_CONFIRMED,
            ),
        ]
        prompt = CognitiveHandoff._format_belief_for_prompt(belief, context)
        assert "The API uses gRPC" in prompt
        assert "The API uses REST" in prompt
        assert "C3" in prompt
        assert "C4" in prompt

    def test_default_providers(self):
        """Default provider assignments should match the plan."""
        handoff = CognitiveHandoff(router=None)
        assert handoff._architect == "openai"
        assert handoff._auditor_premium == "anthropic"
        assert handoff._auditor_economic == "gemini"
        assert handoff._infra == "gemini"
