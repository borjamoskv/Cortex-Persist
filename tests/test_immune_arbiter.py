"""CORTEX — Immune Arbiter + Falsifier Test Suite."""

from __future__ import annotations

import os
import sys

# Ensure project root is accessible
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CORTEX_TESTING", "1")

import pytest

from cortex.engine.forgetting_models import PolicyRecommendation
from cortex.immune.arbiter import (
    ImmuneArbiter,
    Verdict,
)
from cortex.immune.falsification import EvolutionaryFalsifier

# ── EvolutionaryFalsifier ─────────────────────────────────────────────


class TestEvolutionaryFalsifier:
    """Tests for the is_falsifiable() heuristic."""

    def setup_method(self) -> None:
        self.f = EvolutionaryFalsifier()

    def test_falsifiable_with_comparison(self) -> None:
        assert self.f.is_falsifiable("Response time should be less than 200ms")

    def test_falsifiable_with_bound(self) -> None:
        assert self.f.is_falsifiable("Cache hit rate must be at least 80%")

    def test_falsifiable_with_conditional(self) -> None:
        assert self.f.is_falsifiable("If input is null, return 0")

    def test_falsifiable_with_numeric(self) -> None:
        assert self.f.is_falsifiable("Latency is 50ms on average")

    def test_unfalsifiable_trust_me(self) -> None:
        assert not self.f.is_falsifiable("Trust me, it works")

    def test_unfalsifiable_everyone_knows(self) -> None:
        assert not self.f.is_falsifiable("Everyone knows this is true")

    def test_unfalsifiable_it_just_works(self) -> None:
        assert not self.f.is_falsifiable("It just works")

    def test_unfalsifiable_obvious(self) -> None:
        assert not self.f.is_falsifiable("It is obvious that we need this")

    def test_empty_string(self) -> None:
        assert not self.f.is_falsifiable("")

    def test_short_string(self) -> None:
        assert not self.f.is_falsifiable("ok")


# ── ImmuneArbiter Filters ────────────────────────────────────────────


class TestArbiterFilters:
    """Tests for individual F1-F5 filters."""

    def setup_method(self) -> None:
        self.arbiter = ImmuneArbiter()

    def test_f1_read_only_passes(self) -> None:
        plan = {"actions": [{"type": "read"}, {"type": "search"}]}
        f1 = self.arbiter._filter_reversibility(plan)
        assert f1.verdict == Verdict.PASS
        assert f1.score == 100

    def test_f1_push_holds(self) -> None:
        plan = {"actions": [{"type": "push"}]}
        f1 = self.arbiter._filter_reversibility(plan)
        assert f1.verdict == Verdict.HOLD
        assert f1.score == 25  # R3 = 100 - 75

    def test_f2_falsifiable_plan_passes(self) -> None:
        plan = {
            "assumptions": [
                "Response time should be less than 200ms",
                "Cache hit rate must be at least 80%",
            ],
            "actions": [],
        }
        f2 = self.arbiter._filter_adversarial("check", plan)
        assert f2.verdict == Verdict.PASS
        assert f2.score == 100.0

    def test_f2_unfalsifiable_plan_holds(self) -> None:
        plan = {
            "assumptions": [
                "Everyone knows this",
                "It is obvious",
                "Trust me",
            ],
            "actions": [],
        }
        f2 = self.arbiter._filter_adversarial("deploy", plan)
        assert f2.verdict == Verdict.HOLD
        assert f2.score == 0.0

    def test_f2_echo_chamber_detected(self) -> None:
        plan = {
            "actions": [
                {"type": "deploy-prod"},
                {"type": "deploy-staging"},
                {"type": "deploy-backup"},
            ],
        }
        f2 = self.arbiter._filter_adversarial("deploy", plan)
        assert f2.verdict == Verdict.HOLD
        assert f2.score <= 40.0

    def test_f2_no_echo_small_plan(self) -> None:
        plan = {"actions": [{"type": "test"}]}
        f2 = self.arbiter._filter_adversarial("test", plan)
        # Should not trigger echo with < 3 actions
        assert f2.verdict == Verdict.PASS

    def test_f3_valid_plan_passes(self) -> None:
        plan = {
            "actions": [
                {"type": "build", "requires": [], "produces": ["artifact"]},
                {"type": "deploy", "requires": ["artifact"], "produces": ["service"]},
            ],
        }
        f3 = self.arbiter._filter_causal(plan)
        assert f3.verdict == Verdict.PASS
        assert f3.score == 90.0

    def test_f3_missing_prerequisites_holds(self) -> None:
        plan = {
            "actions": [
                {"type": "deploy", "requires": ["artifact", "tests"], "produces": ["service"]},
            ],
        }
        f3 = self.arbiter._filter_causal(plan)
        assert f3.verdict == Verdict.HOLD
        assert f3.score < 90.0

    def test_f3_empty_plan_passes(self) -> None:
        plan = {"actions": []}
        f3 = self.arbiter._filter_causal(plan)
        assert f3.verdict == Verdict.PASS
        assert f3.score == 100.0

    def test_f4_net_negative_entropy_passes(self) -> None:
        plan = {"added_lines": 10, "removed_lines": 50, "fixme_resolved": 3}
        f4 = self.arbiter._filter_entropy(plan)
        assert f4.verdict == Verdict.PASS

    def test_f4_high_entropy_holds(self) -> None:
        plan = {"added_lines": 500, "new_files": 10, "removed_lines": 0}
        f4 = self.arbiter._filter_entropy(plan)
        assert f4.verdict == Verdict.HOLD

    def test_f5_high_confidence_passes(self) -> None:
        f5 = self.arbiter._filter_confidence(0.9, 100.0)
        assert f5.verdict == Verdict.PASS

    def test_f5_low_confidence_holds(self) -> None:
        f5 = self.arbiter._filter_confidence(0.1, 25.0)
        assert f5.verdict == Verdict.HOLD


# ── Triage Integration ───────────────────────────────────────────────


class TestTriage:
    """End-to-end triage tests."""

    def setup_method(self) -> None:
        self.arbiter = ImmuneArbiter()

    @pytest.mark.asyncio
    async def test_safe_plan_passes(self) -> None:
        plan = {
            "actions": [{"type": "read"}],
            "added_lines": 0,
            "removed_lines": 10,
        }
        result = await self.arbiter.triage("check health", plan, confidence=0.9)
        assert result.verdict == Verdict.PASS
        assert result.immunity_certificate is True

    @pytest.mark.asyncio
    async def test_risky_plan_holds(self) -> None:
        plan = {
            "actions": [{"type": "push"}, {"type": "deploy"}],
            "added_lines": 500,
            "new_files": 20,
        }
        result = await self.arbiter.triage("deploy all", plan, confidence=0.3)
        assert result.verdict == Verdict.HOLD
        assert result.blast_radius > 0


# ── PolicyRecommendation Completeness ────────────────────────────────


class TestPolicyRecommendation:
    def test_all_values_present(self) -> None:
        values = [e.value for e in PolicyRecommendation]
        assert "OPTIMAL" in values
        assert "PROTECT_CAUSAL_ROOTS" in values
        assert len(values) == 5
