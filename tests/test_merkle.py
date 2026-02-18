"""
Tests for the canonical Merkle tree implementations.

Tests both:
  - cortex.consensus.merkle (used by vote_ledger)
  - cortex.engine.ledger (used by ImmutableLedger)
"""

import hashlib

import pytest

# ── consensus/merkle.py ──────────────────────────────────────────────


from cortex.consensus.merkle import MerkleTree, compute_merkle_root, verify_merkle_proof


class TestComputeMerkleRoot:
    def test_empty_list_returns_empty(self):
        assert compute_merkle_root([]) == ""

    def test_single_hash(self):
        h = hashlib.sha256(b"hello").hexdigest()
        assert compute_merkle_root([h]) == h

    def test_two_hashes(self):
        a = hashlib.sha256(b"a").hexdigest()
        b = hashlib.sha256(b"b").hexdigest()
        expected = hashlib.sha256(f"{a}{b}".encode()).hexdigest()
        assert compute_merkle_root([a, b]) == expected

    def test_odd_number_of_hashes(self):
        """Odd element at end should be duplicated for pairing."""
        hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(3)]
        root = compute_merkle_root(hashes)
        assert isinstance(root, str)
        assert len(root) == 64

    def test_determinism(self):
        hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(10)]
        assert compute_merkle_root(hashes) == compute_merkle_root(hashes)


class TestVerifyMerkleProof:
    """Regression: verify_merkle_proof was missing a return statement (always None)."""

    def test_valid_proof(self):
        items = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4)]
        tree = MerkleTree(items)
        proof = tree.get_proof(0)
        result = verify_merkle_proof(items[0], proof, tree.root)
        assert result is True

    def test_invalid_leaf_rejects(self):
        items = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4)]
        tree = MerkleTree(items)
        proof = tree.get_proof(0)
        fake_leaf = hashlib.sha256(b"FAKE").hexdigest()
        result = verify_merkle_proof(fake_leaf, proof, tree.root)
        assert result is False

    def test_invalid_root_rejects(self):
        items = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4)]
        tree = MerkleTree(items)
        proof = tree.get_proof(2)
        result = verify_merkle_proof(items[2], proof, "0" * 64)
        assert result is False

    def test_empty_proof_single_leaf(self):
        """Single-element tree has empty proof, leaf == root."""
        h = hashlib.sha256(b"solo").hexdigest()
        tree = MerkleTree([h])
        proof = tree.get_proof(0)
        assert verify_merkle_proof(h, proof, tree.root) is True


class TestMerkleTreeConsensus:
    def test_root_deterministic(self):
        items = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(8)]
        t1 = MerkleTree(items)
        t2 = MerkleTree(items)
        assert t1.root == t2.root

    def test_empty_tree(self):
        tree = MerkleTree([])
        assert tree.root == ""

    def test_proof_for_every_leaf(self):
        items = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(7)]
        tree = MerkleTree(items)
        for idx, leaf in enumerate(items):
            proof = tree.get_proof(idx)
            assert verify_merkle_proof(leaf, proof, tree.root), f"Proof failed for leaf {idx}"

    def test_out_of_bounds_proof(self):
        items = [hashlib.sha256(b"x").hexdigest()]
        tree = MerkleTree(items)
        assert tree.get_proof(-1) == []
        assert tree.get_proof(99) == []

    def test_root_matches_compute_merkle_root(self):
        """MerkleTree.root should agree with the standalone compute_merkle_root."""
        items = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(16)]
        tree = MerkleTree(items)
        assert tree.root == compute_merkle_root(items)
