"""Open CORTEX — Persistence Layer Tests.

Tests all 6 MemoryStore operations:
  write_memory, get_memory, search_canonical,
  reconsolidate, get_audit_trail, get_version_chain

Uses a temporary SQLite database for isolation.
"""

from __future__ import annotations

import pytest

from open_cortex.models import (
    Memory,
    Namespace,
    Provenance,
    SourceType,
    ProvenanceMethod,
)
from open_cortex.persistence import MemoryStore


@pytest.fixture
def store(tmp_path):
    """Fresh MemoryStore per test."""
    db_path = str(tmp_path / "test_ocx.db")
    return MemoryStore(db_path=db_path)


# ─── Write & Read ────────────────────────────────────────────────────


class TestWriteAndRead:

    def test_write_and_get(self, store):
        mem = Memory(content="CORTEX uses AES-256-GCM", tags=["security"])
        store.write_memory(mem)
        got = store.get_memory(mem.id)
        assert got is not None
        assert got.content == "CORTEX uses AES-256-GCM"
        assert "security" in got.tags

    def test_write_with_namespace(self, store):
        mem = Memory(
            content="Team-level fact",
            namespace=Namespace.TEAM,
        )
        store.write_memory(mem)
        got = store.get_memory(mem.id)
        assert got is not None
        assert got.namespace == Namespace.TEAM

    def test_get_nonexistent_returns_none(self, store):
        assert store.get_memory("nonexistent_id_xyz") is None

    def test_write_with_provenance(self, store):
        mem = Memory(
            content="From documentation",
            provenance=Provenance(
                source=SourceType.DOCUMENT,
                method=ProvenanceMethod.EXTRACTION,
                author="borjamoskv",
            ),
        )
        store.write_memory(mem)
        got = store.get_memory(mem.id)
        assert got is not None
        assert got.provenance.source == SourceType.DOCUMENT

    def test_count(self, store):
        assert store.count() == 0
        store.write_memory(Memory(content="fact 1"))
        store.write_memory(Memory(content="fact 2"))
        assert store.count() == 2


# ─── Search ──────────────────────────────────────────────────────────


class TestSearch:

    def test_search_by_text(self, store):
        store.write_memory(Memory(content="Python is great for ML"))
        store.write_memory(Memory(content="Rust is fast"))
        results = store.search_canonical(text_query="Python")
        assert len(results) >= 1
        assert any("Python" in m.content for m in results)

    def test_search_by_tag(self, store):
        store.write_memory(Memory(content="fact A", tags=["alpha"]))
        store.write_memory(Memory(content="fact B", tags=["beta"]))
        results = store.search_canonical(tags=["alpha"])
        assert len(results) == 1
        assert results[0].content == "fact A"

    def test_search_by_confidence(self, store):
        from open_cortex.models import Belief
        mem = Memory(content="high conf fact", belief=Belief(confidence=0.95))
        store.write_memory(mem)
        mem_low = Memory(content="low conf fact", belief=Belief(confidence=0.1))
        store.write_memory(mem_low)
        results = store.search_canonical(min_confidence=0.5)
        assert len(results) == 1
        assert results[0].content == "high conf fact"

    def test_search_empty_db(self, store):
        results = store.search_canonical()
        assert results == []


# ─── Reconsolidation ─────────────────────────────────────────────────


class TestReconsolidation:

    def test_basic_reconsolidation(self, store):
        original = Memory(content="Old fact")
        store.write_memory(original)

        new_id, audit_id = store.reconsolidate(
            target_id=original.id,
            new_content="Updated fact",
            confidence=0.9,
            reason="Corrected based on new evidence",
        )

        # Original is no longer canonical
        old = store.get_memory(original.id)
        assert old is not None
        assert not old.freshness.is_canonical

        # New version is canonical
        new = store.get_memory(new_id)
        assert new is not None
        assert new.content == "Updated fact"
        assert new.freshness.is_canonical
        assert new.version.parent_id == original.id

    def test_reconsolidate_nonexistent_raises(self, store):
        with pytest.raises(ValueError, match="not found"):
            store.reconsolidate(
                target_id="nonexistent",
                new_content="New",
                confidence=0.5,
                reason="test",
            )


# ─── Audit Trail ─────────────────────────────────────────────────────


class TestAuditTrail:

    def test_audit_trail_on_write(self, store):
        mem = Memory(content="Audited fact")
        store.write_memory(mem)
        trail = store.get_audit_trail(mem.id)
        assert len(trail) >= 1
        assert trail[0].action == "create"

    def test_audit_trail_on_reconsolidate(self, store):
        mem = Memory(content="Original")
        store.write_memory(mem)
        new_id, _ = store.reconsolidate(
            target_id=mem.id,
            new_content="Updated",
            confidence=0.9,
            reason="Correction",
        )
        # Audit trail for the NEW memory shows create
        trail_new = store.get_audit_trail(new_id)
        assert len(trail_new) >= 1
        assert trail_new[0].action == "create"


# ─── Version Chain ───────────────────────────────────────────────────


class TestVersionChain:

    def test_chain_after_reconsolidation(self, store):
        v1 = Memory(content="Version 1")
        store.write_memory(v1)
        v2_id, _ = store.reconsolidate(
            target_id=v1.id,
            new_content="Version 2",
            confidence=0.8,
            reason="Updated",
        )
        v3_id, _ = store.reconsolidate(
            target_id=v2_id,
            new_content="Version 3",
            confidence=0.9,
            reason="Further updated",
        )
        chain = store.get_version_chain(v3_id)
        # Chain is a list of memory IDs from oldest to newest
        assert len(chain) == 3
        assert chain[0] == v1.id  # Oldest
        assert chain[-1] == v3_id  # Newest

    def test_chain_single_memory(self, store):
        mem = Memory(content="Solo fact")
        store.write_memory(mem)
        chain = store.get_version_chain(mem.id)
        assert len(chain) == 1
