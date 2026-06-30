# [C5-REAL] Exergy-Maximized
"""Tests for cortex.consensus.merkle - Merkle Tree Utilities.

C5-REAL audit remediation: consensus/ had 0% test coverage.
"""

import hashlib
import pytest

from babylon60.consensus.merkle import compute_merkle_root, verify_merkle_proof, MerkleTree


# ── compute_merkle_root ──────────────────────────────────────────────────


class TestComputeMerkleRoot:
    """Tests for the standalone compute_merkle_root function."""

    def test_empty_list_returns_empty_string(self):
        assert compute_merkle_root([]) == ""

    def test_single_hash_returns_itself(self):
        h = hashlib.sha256(b"leaf_0").hexdigest()
        assert compute_merkle_root([h]) == h

    def test_two_hashes_deterministic(self):
        h0 = hashlib.sha256(b"leaf_0").hexdigest()
        h1 = hashlib.sha256(b"leaf_1").hexdigest()
        expected = hashlib.sha256(f"{h0}{h1}".encode()).hexdigest()
        assert compute_merkle_root([h0, h1]) == expected

    def test_odd_number_duplicates_last(self):
        hashes = [hashlib.sha256(f"leaf_{i}".encode()).hexdigest() for i in range(3)]
        # With 3 leaves: pair (0,1) and (2,2-dup)
        root = compute_merkle_root(hashes)
        assert isinstance(root, str)
        assert len(root) == 64  # SHA-256 hex

    def test_four_hashes_balanced_tree(self):
        hashes = [hashlib.sha256(f"leaf_{i}".encode()).hexdigest() for i in range(4)]
        root = compute_merkle_root(hashes)
        # Manually compute
        h01 = hashlib.sha256(f"{hashes[0]}{hashes[1]}".encode()).hexdigest()
        h23 = hashlib.sha256(f"{hashes[2]}{hashes[3]}".encode()).hexdigest()
        expected_root = hashlib.sha256(f"{h01}{h23}".encode()).hexdigest()
        assert root == expected_root

    def test_deterministic_same_input_same_output(self):
        hashes = [hashlib.sha256(f"leaf_{i}".encode()).hexdigest() for i in range(5)]
        r1 = compute_merkle_root(hashes)
        r2 = compute_merkle_root(hashes)
        assert r1 == r2

    def test_different_order_different_root(self):
        hashes = [hashlib.sha256(f"leaf_{i}".encode()).hexdigest() for i in range(4)]
        r1 = compute_merkle_root(hashes)
        r2 = compute_merkle_root(list(reversed(hashes)))
        assert r1 != r2


# ── MerkleTree class ─────────────────────────────────────────────────────


class TestMerkleTree:
    """Tests for the MerkleTree class."""

    def _make_leaves(self, n: int) -> list[str]:
        return [hashlib.sha256(f"leaf_{i}".encode()).hexdigest() for i in range(n)]

    def test_root_matches_standalone_function(self):
        leaves = self._make_leaves(4)
        tree = MerkleTree(leaves)
        assert tree.root == compute_merkle_root(leaves)

    def test_empty_tree_root_is_empty(self):
        tree = MerkleTree([])
        assert tree.root == ""

    def test_single_leaf_root_is_leaf(self):
        leaves = self._make_leaves(1)
        tree = MerkleTree(leaves)
        assert tree.root == leaves[0]

    def test_get_proof_invalid_index_returns_empty(self):
        tree = MerkleTree(self._make_leaves(4))
        assert tree.get_proof(-1) == []
        assert tree.get_proof(4) == []
        assert tree.get_proof(100) == []

    def test_proof_verifies_for_all_leaves(self):
        for n in [2, 3, 4, 5, 7, 8, 16]:
            leaves = self._make_leaves(n)
            tree = MerkleTree(leaves)
            for idx in range(n):
                proof = tree.get_proof(idx)
                assert verify_merkle_proof(leaves[idx], proof, tree.root), (
                    f"Proof failed for leaf {idx} in tree of size {n}"
                )

    def test_tampered_leaf_fails_verification(self):
        leaves = self._make_leaves(4)
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)
        tampered_hash = hashlib.sha256(b"TAMPERED").hexdigest()
        assert not verify_merkle_proof(tampered_hash, proof, tree.root)

    def test_tampered_root_fails_verification(self):
        leaves = self._make_leaves(4)
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)
        fake_root = hashlib.sha256(b"FAKE_ROOT").hexdigest()
        assert not verify_merkle_proof(leaves[0], proof, fake_root)

    def test_tree_levels_correct_count(self):
        leaves = self._make_leaves(8)
        tree = MerkleTree(leaves)
        # 8 leaves → 4 → 2 → 1 = 4 levels
        assert len(tree.tree) == 4

    def test_large_tree_proof_valid(self):
        leaves = self._make_leaves(100)
        tree = MerkleTree(leaves)
        # Spot check first, middle, last
        for idx in [0, 49, 99]:
            proof = tree.get_proof(idx)
            assert verify_merkle_proof(leaves[idx], proof, tree.root)
