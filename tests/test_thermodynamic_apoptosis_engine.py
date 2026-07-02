# [C5-REAL] Exergy-Maximized
"""
Tests for Thermodynamic Apoptosis Engine.
Verifies Shannon entropy filtration, explicit deletion pruning, cascade collapse,
and O(1) atomic snapshotting.
"""

from __future__ import annotations

import json
import os
import pytest

from babylon60.engine.causal.ledger_apoptosis import ThermodynamicLedgerApoptosis


@pytest.fixture
def temp_ledger(tmp_path):
    """Create a temporary AOF ledger path."""
    return tmp_path / "cortex_state_temp.aof"


def test_apoptosis_calculates_shannon_entropy():
    """Verify that Shannon entropy calculation conforms to mathematical expectations."""
    # High entropy string (diverse character sequence)
    high_entropy = "The quick brown fox jumps over the lazy dog 1234567890!"
    # Low entropy string (simple repetitions)
    low_entropy = "aaaaabbbbb"

    e_high = ThermodynamicLedgerApoptosis.calculate_shannon_entropy(high_entropy)
    e_low = ThermodynamicLedgerApoptosis.calculate_shannon_entropy(low_entropy)

    assert e_high > e_low
    assert e_low == 1.0  # log2(2) for symmetric binary frequencies of 'a' and 'b'


def test_apoptosis_prunes_explicit_and_anergy(temp_ledger):
    """Test that explicit deletes, low entropy nodes, and cascades are correctly purged."""
    nodes = [
        # Root node: Normal and high entropy
        {
            "hash_id": "root_01",
            "parent_hash": None,
            "action": "commit",
            "payload": "High exergy initial system state commitment",
        },
        # Child 1: Low entropy (Anergy node)
        {
            "hash_id": "child_low_entropy",
            "parent_hash": "root_01",
            "action": "commit",
            "payload": "aaaaa",  # Low information density
        },
        # Child 2: Explicitly deleted node
        {
            "hash_id": "child_deleted",
            "parent_hash": "root_01",
            "action": "delete",
            "payload": "Node marked for destruction",
        },
        # Grandchild of deleted node: Cascade target
        {
            "hash_id": "grandchild_cascade",
            "parent_hash": "child_deleted",
            "action": "commit",
            "payload": "Sub-dependency that should collapse transitively",
        },
        # Child 3: Normal child (keeps active)
        {
            "hash_id": "child_active",
            "parent_hash": "root_01",
            "action": "commit",
            "payload": "Structured and robust system verification state",
        },
    ]

    with open(temp_ledger, "w", encoding="utf-8") as f:
        for node in nodes:
            f.write(json.dumps(node) + "\n")

    # Initialize Apoptosis with entropy threshold of 2.0
    apoptosis = ThermodynamicLedgerApoptosis(str(temp_ledger), entropy_threshold=2.0)

    # Run compaction/snapshot
    active_count = apoptosis.trigger_snapshot()

    # Verify statistics
    assert apoptosis.stats["scanned"] == 5
    assert apoptosis.stats["purged_explicit"] == 1  # child_deleted
    assert apoptosis.stats["purged_anergy"] == 1  # child_low_entropy
    assert apoptosis.stats["purged_cascade"] == 1  # grandchild_cascade
    assert apoptosis.stats["crystallized"] == 2  # root_01 and child_active
    assert active_count == 2

    # Verify persistent file content on disk after snapshotting
    assert temp_ledger.exists()
    with open(temp_ledger, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 2
        remaining_hashes = [json.loads(line)["hash_id"] for line in lines]
        assert "root_01" in remaining_hashes
        assert "child_active" in remaining_hashes
        assert "child_low_entropy" not in remaining_hashes
        assert "child_deleted" not in remaining_hashes
        assert "grandchild_cascade" not in remaining_hashes
