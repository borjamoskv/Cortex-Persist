# [C5-REAL] Exergy-Maximized
"""Tests for babylon60.audit.anchor — Merkle Root Anchoring Service."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from babylon60.audit.anchor import AnchorService, MerkleTree, MerkleNode


def test_merkle_tree_empty_throws():
    with pytest.raises(ValueError):
        MerkleTree([])


def test_merkle_tree_single_leaf():
    h = "a" * 64
    tree = MerkleTree([h])
    assert tree.root_hash == h


def test_merkle_tree_two_leaves():
    h1 = "a" * 64
    h2 = "b" * 64
    tree = MerkleTree([h1, h2])
    # Recalculate manually
    expected = MerkleTree._hash_pair(h1, h2)
    assert tree.root_hash == expected


def test_merkle_tree_odd_leaves():
    h1 = "a" * 64
    h2 = "b" * 64
    h3 = "c" * 64
    # Three leaves: nodes = [h1, h2, h3]. Odd → appends h3 again.
    # Level 1: hash_pair(h1, h2) and hash_pair(h3, h3)
    # Level 2: hash_pair(hash_pair(h1, h2), hash_pair(h3, h3))
    tree = MerkleTree([h1, h2, h3])
    p1 = MerkleTree._hash_pair(h1, h2)
    p2 = MerkleTree._hash_pair(h3, h3)
    expected = MerkleTree._hash_pair(p1, p2)
    assert tree.root_hash == expected


def test_anchor_service_lifecycle(tmp_path: Path):
    db_file = str(tmp_path / "anchor_test.db")
    service = AnchorService(db_path=db_file, epoch_size=3)
    
    assert service.current_epoch == 1
    assert len(service.pending_hashes) == 0

    # Ingest 1
    h1 = "1" * 64
    anchor = service.ingest_tx_hash(h1)
    assert anchor is None
    assert len(service.pending_hashes) == 1

    # Ingest 2
    h2 = "2" * 64
    anchor = service.ingest_tx_hash(h2)
    assert anchor is None
    assert len(service.pending_hashes) == 2

    # Ingest 3 (reaches epoch_size of 3)
    h3 = "3" * 64
    anchor = service.ingest_tx_hash(h3)
    assert anchor is not None
    assert anchor.epoch_id == 1
    assert anchor.tx_count == 3
    assert anchor.anchor_target == "arbitrum"
    assert len(service.pending_hashes) == 0
    assert service.current_epoch == 2

    # Verify db status
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.execute("SELECT epoch_id, merkle_root, tx_count FROM merkle_anchors")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == anchor.merkle_root
        assert rows[0][2] == 3
    finally:
        conn.close()

    # Ingest next epoch
    h4 = "4" * 64
    service.ingest_tx_hash(h4)
    assert service.current_epoch == 2
    assert len(service.pending_hashes) == 1


def test_anchor_service_verify_epoch(tmp_path: Path):
    db_file = str(tmp_path / "anchor_test.db")
    service = AnchorService(db_path=db_file, epoch_size=2)

    h1 = "a" * 64
    h2 = "b" * 64
    anchor = service.ingest_tx_hash(h1)
    assert anchor is None
    anchor = service.ingest_tx_hash(h2)
    assert anchor is not None

    # Verification passes with correct hashes
    assert service.verify_epoch(epoch_id=1, tx_hashes=[h1, h2]) is True

    # Verification fails with tampered hashes
    assert service.verify_epoch(epoch_id=1, tx_hashes=[h1, "c" * 64]) is False

    # Verification fails for non-existent epoch
    with pytest.raises(ValueError):
        service.verify_epoch(epoch_id=99, tx_hashes=[h1, h2])
