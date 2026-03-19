"""Tests for autodidact marketing agents (EvangelistAgent + AnalystAgent)."""

from __future__ import annotations

from unittest.mock import patch

from cortex.extensions.moltbook.agents import (
    _ANALYST_PROMPTS,
    _EVANGELIST_PROMPTS,
)


class TestEvangelistPrompts:
    """EvangelistAgent prompt catalog validation."""

    def test_prompt_catalog_compliance_focused(self):
        """All evangelist prompts reference regulation or compliance."""
        compliance_terms = {
            "article 12",
            "audit trail",
            "compliance",
            "eu ai act",
            "record-keeping",
            "hash-chain",
            "ledger",
            "non-compliance",
            "annex iii",
            "auditor",
            "retroactive",
        }
        for prompt in _EVANGELIST_PROMPTS:
            lower = prompt.lower()
            assert any(t in lower for t in compliance_terms), (
                f"Prompt not compliance-focused: {prompt[:60]}..."
            )

    def test_prompt_catalog_nonzero(self):
        assert len(_EVANGELIST_PROMPTS) >= 5


class TestAnalystPrompts:
    """AnalystAgent prompt catalog validation."""

    def test_prompt_catalog_regulatory_focused(self):
        """All analyst prompts reference regulatory intelligence."""
        regulatory_terms = {
            "enforcement",
            "compliance",
            "eu ai act",
            "regulatory",
            "annex iii",
            "article 12",
            "supervisory",
            "high-risk",
        }
        for prompt in _ANALYST_PROMPTS:
            lower = prompt.lower()
            assert any(t in lower for t in regulatory_terms), (
                f"Prompt not regulatory-focused: {prompt[:60]}..."
            )

    def test_prompt_catalog_nonzero(self):
        assert len(_ANALYST_PROMPTS) >= 3


class TestMarketingMode:
    """MoltbookLegionEngine marketing mode."""

    @patch(
        "cortex.extensions.moltbook.legion_engine.SubmarineCable",
    )
    @patch(
        "cortex.extensions.moltbook.legion_engine.TutorAgent",
    )
    def test_marketing_mode_spawns_correct_agents(
        self,
        mock_tutor,
        mock_cable,
    ):
        from cortex.extensions.moltbook.legion_engine import (
            MoltbookLegionEngine,
        )

        engine = MoltbookLegionEngine(
            mode="marketing",
            evangelist_count=2,
            analyst_count=1,
            use_cables=False,
        )
        assert len(engine.evangelists) == 2
        assert len(engine.analysts) == 1
        assert len(engine.vanguards) == 0
        assert len(engine.shadows) <= 2

    @patch(
        "cortex.extensions.moltbook.legion_engine.SubmarineCable",
    )
    @patch(
        "cortex.extensions.moltbook.legion_engine.TutorAgent",
    )
    def test_combat_mode_no_evangelists(
        self,
        mock_tutor,
        mock_cable,
    ):
        from cortex.extensions.moltbook.legion_engine import (
            MoltbookLegionEngine,
        )

        engine = MoltbookLegionEngine(
            mode="combat",
            agent_count=5,
            subagent_count=5,
            use_cables=False,
        )
        assert len(engine.vanguards) == 5
        assert len(engine.shadows) == 5
        assert len(engine.evangelists) == 0
        assert len(engine.analysts) == 0
