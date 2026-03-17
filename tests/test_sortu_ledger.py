"""Tests for sortu_ledger.py — Skill lifecycle persistence."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_scripts = Path.home() / ".gemini" / "antigravity" / "skills" / "Sortu" / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from sortu_ledger import SkillLedger
from sortu_models import (
    AbortReason,
    SkillRecord,
    SortuState,
    YieldEvent,
)


@pytest.fixture
def db():
    """In-memory SQLite database for tests."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def ledger(db):
    return SkillLedger(db)


@pytest.fixture
def sample_record():
    return SkillRecord.new(
        skill_name="test-skill",
        version="1.0.0",
        artifact_hashes={"SKILL.md": "abc123", "schema.json": "def456"},
        ttl_days=7,
    )


class TestRegisterAndGet:
    def test_register_and_retrieve(self, ledger, sample_record):
        ledger.register(sample_record)
        retrieved = ledger.get(sample_record.skill_id)
        assert retrieved is not None
        assert retrieved.skill_name == "test-skill"
        assert retrieved.state == SortuState.DRAFT
        assert retrieved.artifact_hashes["SKILL.md"] == "abc123"

    def test_get_nonexistent_returns_none(self, ledger):
        assert ledger.get("does-not-exist") is None


class TestTransition:
    def test_valid_transition(self, ledger, sample_record):
        ledger.register(sample_record)
        ledger.transition(sample_record.skill_id, SortuState.AUDITED)
        record = ledger.get(sample_record.skill_id)
        assert record.state == SortuState.AUDITED

    def test_illegal_transition_raises(self, ledger, sample_record):
        ledger.register(sample_record)
        with pytest.raises(ValueError, match="Illegal transition"):
            ledger.transition(sample_record.skill_id, SortuState.ACTIVE)

    def test_nonexistent_skill_raises(self, ledger):
        with pytest.raises(ValueError, match="not found"):
            ledger.transition("ghost-id", SortuState.AUDITED)

    def test_abort_stores_reason(self, ledger, sample_record):
        ledger.register(sample_record)
        ledger.transition(
            sample_record.skill_id,
            SortuState.ABORTED,
            abort_reason=AbortReason.REDUNDANT_COMPUTATION,
        )
        record = ledger.get(sample_record.skill_id)
        assert record.state == SortuState.ABORTED
        assert record.abort_reason == AbortReason.REDUNDANT_COMPUTATION

    def test_verified_sets_status(self, ledger, sample_record):
        ledger.register(sample_record)
        ledger.transition(sample_record.skill_id, SortuState.AUDITED)
        ledger.transition(sample_record.skill_id, SortuState.FORGED)
        ledger.transition(sample_record.skill_id, SortuState.VERIFIED)
        record = ledger.get(sample_record.skill_id)
        assert record.verification_status == "PASS"


class TestYieldEvents:
    def test_record_yield_event(self, ledger, sample_record):
        ledger.register(sample_record)
        event = YieldEvent(hours_saved=2.5, days_since=3, verified=True)
        ledger.record_yield_event(sample_record.skill_id, event)

        record = ledger.get(sample_record.skill_id)
        assert len(record.yield_events) == 1
        assert record.yield_events[0].hours_saved == 2.5

    def test_multiple_yield_events(self, ledger, sample_record):
        ledger.register(sample_record)
        ledger.record_yield_event(
            sample_record.skill_id,
            YieldEvent(hours_saved=1.0, days_since=1),
        )
        ledger.record_yield_event(
            sample_record.skill_id,
            YieldEvent(hours_saved=3.0, days_since=5),
        )
        record = ledger.get(sample_record.skill_id)
        assert len(record.yield_events) == 2


class TestListByState:
    def test_list_by_state(self, ledger):
        r1 = SkillRecord.new("skill-a", "1.0", {"x": "1"})
        r2 = SkillRecord.new("skill-b", "1.0", {"x": "2"})
        ledger.register(r1)
        ledger.register(r2)
        ledger.transition(r1.skill_id, SortuState.AUDITED)

        drafts = ledger.list_by_state(SortuState.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].skill_name == "skill-b"

        audited = ledger.list_by_state(SortuState.AUDITED)
        assert len(audited) == 1
        assert audited[0].skill_name == "skill-a"


class TestQuarantineCandidates:
    def test_expired_ttl_appears(self, ledger):
        record = SkillRecord.new("old-skill", "1.0", {"x": "1"}, ttl_days=0)
        # Manually set ttl to past
        record.ttl_expiration = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        ledger.register(record)

        # Advance to ACTIVE
        for state in [
            SortuState.AUDITED,
            SortuState.FORGED,
            SortuState.VERIFIED,
            SortuState.LINKED,
            SortuState.LEDGERED,
            SortuState.ACTIVE,
        ]:
            ledger.transition(record.skill_id, state)

        candidates = ledger.list_quarantine_candidates()
        assert len(candidates) == 1
        assert candidates[0].skill_name == "old-skill"

    def test_fresh_ttl_not_candidate(self, ledger):
        record = SkillRecord.new("fresh-skill", "1.0", {"x": "1"}, ttl_days=30)
        ledger.register(record)
        for state in [
            SortuState.AUDITED,
            SortuState.FORGED,
            SortuState.VERIFIED,
            SortuState.LINKED,
            SortuState.LEDGERED,
            SortuState.ACTIVE,
        ]:
            ledger.transition(record.skill_id, state)

        candidates = ledger.list_quarantine_candidates()
        assert len(candidates) == 0


class TestFullLifecycle:
    def test_draft_to_purge(self, ledger, sample_record):
        """Full lifecycle: DRAFT → AUDITED → ... → ACTIVE → QUARANTINED → TOMBSTONED → PURGED."""
        ledger.register(sample_record)

        for state in [
            SortuState.AUDITED,
            SortuState.FORGED,
            SortuState.VERIFIED,
            SortuState.LINKED,
            SortuState.LEDGERED,
            SortuState.ACTIVE,
            SortuState.QUARANTINED,
            SortuState.TOMBSTONED,
            SortuState.PURGED,
        ]:
            ledger.transition(sample_record.skill_id, state)

        record = ledger.get(sample_record.skill_id)
        assert record.state == SortuState.PURGED
        assert record.purge_status == "PURGED"
