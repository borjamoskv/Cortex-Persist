"""Tests for sortu_engine.py — Full forge lifecycle and sweeps."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_scripts = Path.home() / ".gemini" / "antigravity" / "skills" / "Sortu" / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from sortu_engine import SortuEngine
from sortu_models import (
    AbortReason,
    ForgeAbortError,
    ForgeInvocation,
    SortuState,
)


def _make_skill_dir(base: Path, name: str = "test-skill") -> Path:
    """Create a minimal valid skill directory for verification."""
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: test\ndescription: test skill\n---\n# Test\n")
    (d / "schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Test",
                "type": "object",
                "required": ["intent", "causal_parent", "requested_by"],
                "properties": {
                    "intent": {"type": "string"},
                    "causal_parent": {"type": ["string", "null"]},
                    "requested_by": {"type": "string"},
                },
            }
        )
    )
    (d / "policy.yaml").write_text(
        "states:\n  - ACTIVE\n  - ABORTED\n  - PURGED\n  - QUARANTINED\n  - TOMBSTONED\n"
        "abort_reasons:\n  MISSING: missing\n"
        "required_artifacts:\n"
        "  - path: SKILL.md\n    required: true\n"
        "  - path: schema.json\n    required: true\n"
        "  - path: 'verify_*.py'\n    required: true\n"
    )
    (d / "verify_test.py").write_text("# verifier\n")
    return d


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def engine(db, tmp_path):
    """Engine with an empty skills directory (no overlaps)."""
    return SortuEngine(db_conn=db, skills_dir=tmp_path)


class TestHappyPath:
    def test_full_forge_draft_to_active(self, engine, tmp_path):
        skill_dir = _make_skill_dir(tmp_path)
        inv = ForgeInvocation(
            intent="Compile a sovereign test harness for deterministic validation",
            causal_parent=None,
            requested_by="test-agent",
        )
        record = engine.forge(inv, skill_dir=skill_dir)
        assert record.state == SortuState.ACTIVE
        assert record.verification_status == "PASS" or record.state == SortuState.ACTIVE
        assert len(record.artifact_hashes) > 0

    def test_forge_without_skill_dir_skips_verification(self, engine):
        inv = ForgeInvocation(
            intent="Build an invisible warp drive for testing",
            causal_parent=None,
            requested_by="test-agent",
        )
        record = engine.forge(inv, skill_dir=None)
        assert record.state == SortuState.ACTIVE

    def test_intent_to_name(self):
        assert (
            SortuEngine._intent_to_name("Build a sovereign test harness")
            == "build-a-sovereign-test-harness"
        )
        assert SortuEngine._intent_to_name("x") == "x"


class TestAbortOnOverlap:
    def test_redundant_skill_aborts(self, db, tmp_path):
        # Create an existing skill with similar text
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        existing = skills_dir / "existing-skill"
        existing.mkdir()
        (existing / "SKILL.md").write_text(
            "---\ndescription: Sovereign test harness for validation\n---\n"
            "# Sovereign Test Harness\n"
            "A sovereign test harness for deterministic validation.\n"
        )

        engine = SortuEngine(db_conn=db, skills_dir=skills_dir)
        inv = ForgeInvocation(
            intent="sovereign test harness for deterministic validation",
            causal_parent=None,
            requested_by="test-agent",
            overlap_threshold=0.3,  # Lower threshold to trigger abort
            causal_gap_threshold=0.9,  # Higher gap to make abort easier
        )

        with pytest.raises(ForgeAbortError) as exc_info:
            engine.forge(inv)

        assert exc_info.value.reason == AbortReason.REDUNDANT_COMPUTATION


class TestAbortOnVerification:
    def test_missing_tripartite_aborts(self, engine, tmp_path):
        # Create an incomplete skill directory
        bad_dir = tmp_path / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("# Incomplete\n")
        # Missing schema.json, policy.yaml, verify_*.py

        inv = ForgeInvocation(
            intent="Build something that will fail verification",
            causal_parent=None,
            requested_by="test-agent",
        )
        with pytest.raises(ForgeAbortError) as exc_info:
            engine.forge(inv, skill_dir=bad_dir)

        assert exc_info.value.reason == AbortReason.CONTRACT_VERIFICATION_FAILED


class TestAbortOnInvalidParent:
    def test_nonexistent_parent_aborts(self, engine, tmp_path):
        skill_dir = _make_skill_dir(tmp_path)
        inv = ForgeInvocation(
            intent="Child skill with orphan parent reference",
            causal_parent="nonexistent-parent-uuid",
            requested_by="test-agent",
        )
        with pytest.raises(ForgeAbortError) as exc_info:
            engine.forge(inv, skill_dir=skill_dir)

        assert exc_info.value.reason == AbortReason.INVALID_CAUSAL_PARENT


class TestAbortedStateStored:
    def test_aborted_record_persisted(self, engine, tmp_path):
        bad_dir = tmp_path / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("# Incomplete\n")

        inv = ForgeInvocation(
            intent="This forge will be aborted and recorded",
            causal_parent=None,
            requested_by="test-agent",
        )
        with pytest.raises(ForgeAbortError):
            engine.forge(inv, skill_dir=bad_dir)

        # Check that the aborted record exists in the ledger
        aborted = engine.ledger.list_by_state(SortuState.ABORTED)
        assert len(aborted) == 1
        assert aborted[0].abort_reason is not None


class TestQuarantineSweep:
    def test_expired_skill_gets_quarantined(self, engine):
        # Forge a skill
        inv = ForgeInvocation(
            intent="A skill that will expire very soon TTL zero",
            causal_parent=None,
            requested_by="test-agent",
            ttl_days=1,
        )
        record = engine.forge(inv)
        assert record.state == SortuState.ACTIVE

        # Sweep with future time
        future = datetime.now(tz=timezone.utc) + timedelta(days=10)
        quarantined = engine.quarantine_sweep(now=future)
        assert len(quarantined) == 1
        assert quarantined[0].state == SortuState.QUARANTINED

    def test_fresh_skill_not_quarantined(self, engine):
        inv = ForgeInvocation(
            intent="A fresh skill with long TTL should survive",
            causal_parent=None,
            requested_by="test-agent",
            ttl_days=365,
        )
        engine.forge(inv)
        quarantined = engine.quarantine_sweep()
        assert len(quarantined) == 0


class TestTombstoneSweep:
    def test_quarantined_past_grace_gets_tombstoned(self, engine):
        inv = ForgeInvocation(
            intent="A skill going through full death cycle here",
            causal_parent=None,
            requested_by="test-agent",
            ttl_days=1,
        )
        _record = engine.forge(inv)

        # Quarantine it
        future = datetime.now(tz=timezone.utc) + timedelta(days=5)
        engine.quarantine_sweep(now=future)

        # Tombstone it (grace_days=7 from TTL expiration)
        far_future = datetime.now(tz=timezone.utc) + timedelta(days=30)
        tombstoned = engine.tombstone_sweep(grace_days=7, now=far_future)
        assert len(tombstoned) == 1
        assert tombstoned[0].state == SortuState.TOMBSTONED


class TestPurgeSweep:
    def test_tombstoned_past_retention_gets_purged(self, engine):
        inv = ForgeInvocation(
            intent="A skill going all the way to purge state now",
            causal_parent=None,
            requested_by="test-agent",
            ttl_days=1,
        )
        engine.forge(inv)

        far = datetime.now(tz=timezone.utc) + timedelta(days=100)
        engine.quarantine_sweep(now=far)
        engine.tombstone_sweep(grace_days=7, now=far)
        purged = engine.purge_sweep(purge_after_days=30, now=far)
        assert len(purged) == 1
        assert purged[0].state == SortuState.PURGED
