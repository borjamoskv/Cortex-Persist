"""Tests for sortu_models.py — State machine, transitions, invocations."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Inject scripts/ into path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent
        / ".gemini"
        / "antigravity"
        / "skills"
        / "Sortu"
        / "scripts"
    ),
)
# Also try the direct path for CI
_scripts = Path.home() / ".gemini" / "antigravity" / "skills" / "Sortu" / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from sortu_models import (
    TRANSITIONS,
    AbortReason,
    ForgeAbortError,
    ForgeInvocation,
    SkillRecord,
    SortuState,
    validate_transition,
)


class TestSortuState:
    def test_all_states_present(self):
        assert len(SortuState) == 11

    def test_terminal_states_have_no_forward(self):
        assert TRANSITIONS[SortuState.PURGED] == []
        assert TRANSITIONS[SortuState.ABORTED] == []


class TestTransitions:
    def test_valid_forward_transitions(self):
        assert validate_transition(SortuState.DRAFT, SortuState.AUDITED) is True
        assert validate_transition(SortuState.AUDITED, SortuState.FORGED) is True
        assert validate_transition(SortuState.ACTIVE, SortuState.QUARANTINED) is True

    def test_abort_from_any_pipeline_state(self):
        for state in [
            SortuState.DRAFT,
            SortuState.AUDITED,
            SortuState.FORGED,
            SortuState.VERIFIED,
            SortuState.LINKED,
            SortuState.LEDGERED,
        ]:
            assert validate_transition(state, SortuState.ABORTED) is True

    def test_illegal_transitions(self):
        assert validate_transition(SortuState.DRAFT, SortuState.ACTIVE) is False
        assert validate_transition(SortuState.ACTIVE, SortuState.DRAFT) is False
        assert validate_transition(SortuState.PURGED, SortuState.ACTIVE) is False
        assert validate_transition(SortuState.ABORTED, SortuState.DRAFT) is False

    def test_quarantined_can_recover_to_active(self):
        assert validate_transition(SortuState.QUARANTINED, SortuState.ACTIVE) is True


class TestForgeInvocation:
    def test_valid_invocation(self):
        inv = ForgeInvocation(
            intent="Build a sovereign test skill",
            causal_parent=None,
            requested_by="test-agent",
        )
        assert inv.overlap_threshold == 0.9
        assert inv.ttl_days == 7

    def test_short_intent_rejected(self):
        with pytest.raises(ValueError, match="at least 8"):
            ForgeInvocation(intent="short", causal_parent=None, requested_by="x")

    def test_empty_requested_by_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            ForgeInvocation(intent="valid intent here", causal_parent=None, requested_by="")

    def test_invalid_overlap_threshold(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            ForgeInvocation(
                intent="valid intent here",
                causal_parent=None,
                requested_by="agent",
                overlap_threshold=1.5,
            )


class TestSkillRecord:
    def test_factory_creates_draft(self):
        record = SkillRecord.new(
            skill_name="test-skill",
            version="1.0.0",
            artifact_hashes={"SKILL.md": "abc123"},
        )
        assert record.state == SortuState.DRAFT
        assert record.skill_name == "test-skill"
        assert record.purge_status == "NONE"
        assert record.abort_reason is None

    def test_factory_with_causal_parent(self):
        record = SkillRecord.new(
            skill_name="child-skill",
            version="1.0.0",
            artifact_hashes={},
            causal_parent="parent-uuid-123",
        )
        assert record.causal_parent == "parent-uuid-123"


class TestForgeAbortError:
    def test_abort_error_carries_reason(self):
        err = ForgeAbortError(AbortReason.REDUNDANT_COMPUTATION, "overlap=0.95")
        assert err.reason == AbortReason.REDUNDANT_COMPUTATION
        assert "overlap=0.95" in str(err)
