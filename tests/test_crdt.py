"""Tests for CRDT Merge Engine — Phase 4."""

from cortex.extensions.sync.crdt import ConflictRecord, CortexCRDT, FactReplica
from cortex.extensions.sync.hlc import HLCTimestamp


def _make_replica(
    fact_id: int,
    content: str,
    fact_type: str = "event",
    node_id: int = 0,
    physical_ms: int = 1000,
    logical: int = 0,
    project: str = "test",
) -> FactReplica:
    """Helper to create FactReplica instances."""
    return FactReplica(
        fact_id=fact_id,
        content=content,
        fact_type=fact_type,
        project=project,
        hlc=HLCTimestamp(physical_ms=physical_ms, logical=logical, node_id=node_id),
        node_id=node_id,
    )


class TestCortexCRDT:
    """CRDT merge tests."""

    def test_new_facts_are_added(self):
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "fact A", node_id=0)]
        remote = [_make_replica(2, "fact B", node_id=1)]

        result = crdt.merge(local, remote)
        assert result.facts_added == 1
        assert result.facts_identical == 0

    def test_identical_facts_are_skipped(self):
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "same content", node_id=0)]
        remote = [_make_replica(1, "same content", node_id=1)]

        result = crdt.merge(local, remote)
        assert result.facts_identical == 1
        assert result.facts_added == 0

    def test_lww_register_remote_wins(self):
        """Non-critical fact: higher HLC wins."""
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "old version", node_id=0, physical_ms=1000)]
        remote = [_make_replica(1, "new version", node_id=1, physical_ms=2000)]

        result = crdt.merge(local, remote)
        assert result.facts_updated == 1

    def test_lww_register_local_wins(self):
        """Non-critical fact: local is newer, so remote is skipped."""
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "newer local", node_id=0, physical_ms=2000)]
        remote = [_make_replica(1, "older remote", node_id=1, physical_ms=1000)]

        result = crdt.merge(local, remote)
        assert result.facts_identical == 1  # local wins, no update

    def test_mv_register_conflict_detection(self):
        """Critical fact (decision): both sides preserved."""
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "decision A", fact_type="decision",
                               node_id=0, physical_ms=1000)]
        remote = [_make_replica(1, "decision B", fact_type="decision",
                                node_id=1, physical_ms=2000)]

        result = crdt.merge(local, remote)
        assert result.conflicts_detected == 1
        assert result.had_conflicts
        assert len(result.conflicts) == 1
        assert result.conflicts[0].local_content == "decision A"
        assert result.conflicts[0].remote_content == "decision B"
        assert result.conflicts[0].resolution == "pending"

    def test_tombstone_handling(self):
        """Tombstoned remote fact increments tombstones counter."""
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "alive fact", node_id=0)]
        remote_tombstoned = _make_replica(1, "", node_id=1)
        remote_tombstoned.is_tombstoned = True

        result = crdt.merge(local, [remote_tombstoned])
        assert result.tombstones_applied == 1

    def test_empty_merge(self):
        crdt = CortexCRDT(local_node_id=0)
        result = crdt.merge([], [])
        assert result.total_processed == 0

    def test_resolve_conflicts_latest(self):
        crdt = CortexCRDT(local_node_id=0)
        conflict = ConflictRecord(
            fact_id=1,
            fact_type="decision",
            project="test",
            local_content="A",
            remote_content="B",
            local_hlc=HLCTimestamp(1000, 0, 0),
            remote_hlc=HLCTimestamp(2000, 0, 1),
            local_node=0,
            remote_node=1,
        )
        resolved = crdt.resolve_conflicts([conflict], strategy="latest")
        assert resolved[0].resolution == "remote_wins"

    def test_resolve_conflicts_local(self):
        crdt = CortexCRDT(local_node_id=0)
        conflict = ConflictRecord(
            fact_id=1,
            fact_type="axiom",
            project="test",
            local_content="A",
            remote_content="B",
            local_hlc=HLCTimestamp(1000, 0, 0),
            remote_hlc=HLCTimestamp(2000, 0, 1),
            local_node=0,
            remote_node=1,
        )
        resolved = crdt.resolve_conflicts([conflict], strategy="local")
        assert resolved[0].resolution == "local_wins"

    def test_tie_break_by_node_id(self):
        """Same HLC: higher node_id wins (deterministic)."""
        crdt = CortexCRDT(local_node_id=0)
        local = [_make_replica(1, "local ver", node_id=0,
                               physical_ms=1000, logical=0)]
        remote = [_make_replica(1, "remote ver", node_id=5,
                                physical_ms=1000, logical=0)]

        result = crdt.merge(local, remote)
        # Remote node_id (5) > local (0), so remote wins
        assert result.facts_updated == 1
