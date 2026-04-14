"""
Tests for the cortex_rs Rust extension and its Python fallback paths.

These tests are designed to pass in two environments:
  1. With `cortex_rs` installed (built via maturin) — exercises the Rust code.
  2. Without `cortex_rs` — exercises the pure-Python fallback in ledger_core
     and integrity_audit.

The tests never import cortex_rs directly; they always go through the
production code, which handles the ImportError gracefully.
"""

from __future__ import annotations

import hashlib

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _pure_python_merkle_root(hashes: list[str]) -> str | None:
    """Reference implementation matching cortex.consensus.merkle.compute_merkle_root."""
    if not hashes:
        return None
    level = list(hashes)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            combined = hashlib.sha256((left + right).encode()).hexdigest()
            next_level.append(combined)
        level = next_level
    return level[0]


# ─── cortex_rs module API (when installed) ────────────────────────────────────

# We import the module conditionally so the test module still loads without it.
try:
    import cortex_rs  # type: ignore[import-not-found]

    _RUST_AVAILABLE = True
except ImportError:
    cortex_rs = None  # type: ignore[assignment]
    _RUST_AVAILABLE = False

_rust_only = pytest.mark.skipif(not _RUST_AVAILABLE, reason="cortex_rs not installed")


@_rust_only
class TestCortexRsModule:
    """Direct tests of the cortex_rs Python module (requires compiled Rust extension)."""

    def test_sha256_hash_known_value(self) -> None:
        # SHA-256("hello") == 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c...
        result = cortex_rs.sha256_hash("hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    def test_sha256_hash_empty_string(self) -> None:
        assert cortex_rs.sha256_hash("") == hashlib.sha256(b"").hexdigest()

    def test_merkle_root_single_leaf(self) -> None:
        leaf = "abc123"
        assert cortex_rs.merkle_root([leaf]) == leaf

    def test_merkle_root_two_leaves(self) -> None:
        a, b = "aa" * 32, "bb" * 32
        expected = hashlib.sha256((a + b).encode()).hexdigest()
        assert cortex_rs.merkle_root([a, b]) == expected

    def test_merkle_root_matches_python_implementation(self) -> None:
        hashes = [hashlib.sha256(f"leaf-{i}".encode()).hexdigest() for i in range(7)]
        py_root = _pure_python_merkle_root(hashes)
        rs_root = cortex_rs.merkle_root(hashes)
        assert rs_root == py_root

    def test_merkle_root_empty(self) -> None:
        assert cortex_rs.merkle_root([]) is None

    def test_verify_ed25519_batch_valid(self) -> None:
        """A correctly signed message must verify as True."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        msg = b"cortex test message"
        sig = private_key.sign(msg)

        pk_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        results = cortex_rs.verify_ed25519_batch([msg], [pk_bytes], [sig])
        assert results == [True]

    def test_verify_ed25519_batch_invalid(self) -> None:
        """A signature over a different message must verify as False."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        sig = private_key.sign(b"correct message")

        pk_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        results = cortex_rs.verify_ed25519_batch([b"wrong message"], [pk_bytes], [sig])
        assert results == [False]

    def test_verify_ed25519_batch_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            cortex_rs.verify_ed25519_batch([b"msg"], [b"\x00" * 32], [])

    def test_verify_ed25519_batch_empty(self) -> None:
        results = cortex_rs.verify_ed25519_batch([], [], [])
        assert results == []


# ─── Ledger integration (production code with Rust or Python fallback) ────────


class TestMerkleTreeLedgerCore:
    """Tests exercising cortex.ledger.ledger_core.MerkleTree / compute_merkle_root.

    These always run regardless of whether cortex_rs is installed.
    """

    def test_merkle_tree_root_hash_matches_pure_python(self) -> None:
        from cortex.ledger.ledger_core import MerkleTree

        hashes = [hashlib.sha256(f"tx-{i}".encode()).hexdigest() for i in range(8)]
        py_root = _pure_python_merkle_root(hashes)
        tree = MerkleTree(hashes)
        assert tree.root_hash == py_root

    def test_merkle_tree_empty(self) -> None:
        from cortex.ledger.ledger_core import MerkleTree

        tree = MerkleTree([])
        assert tree.root_hash is None

    def test_compute_merkle_root_matches_tree(self) -> None:
        from cortex.ledger.ledger_core import MerkleTree, compute_merkle_root

        hashes = [hashlib.sha256(f"h-{i}".encode()).hexdigest() for i in range(5)]
        tree_root = MerkleTree(hashes).root_hash
        fn_root = compute_merkle_root(hashes)
        assert fn_root == tree_root

    def test_compute_merkle_root_empty(self) -> None:
        from cortex.ledger.ledger_core import compute_merkle_root

        assert compute_merkle_root([]) is None

    def test_compute_merkle_root_single(self) -> None:
        from cortex.ledger.ledger_core import compute_merkle_root

        leaf = "deadbeef"
        assert compute_merkle_root([leaf]) == leaf

    def test_verify_proof_round_trip(self) -> None:
        from cortex.ledger.ledger_core import MerkleTree

        hashes = [hashlib.sha256(f"t{i}".encode()).hexdigest() for i in range(6)]
        tree = MerkleTree(hashes)
        for i, leaf in enumerate(hashes):
            proof = tree.get_proof(i)
            assert MerkleTree.verify_proof(leaf, proof, tree.root_hash)  # type: ignore[arg-type]

    @pytest.mark.skipif(_RUST_AVAILABLE, reason="tests the fallback path specifically")
    def test_fallback_path_used_without_rust(self) -> None:
        """When cortex_rs is absent the ledger_core module sets _RUST_AVAILABLE=False."""
        import cortex.ledger.ledger_core as lc

        assert lc._RUST_AVAILABLE is False

    @pytest.mark.skipif(not _RUST_AVAILABLE, reason="tests the Rust acceleration path")
    def test_rust_path_used_with_rust(self) -> None:
        """When cortex_rs is present the ledger_core module sets _RUST_AVAILABLE=True."""
        import cortex.ledger.ledger_core as lc

        assert lc._RUST_AVAILABLE is True


# ─── Integrity Auditor integration ────────────────────────────────────────────


class TestIntegrityAuditorFlags:
    """Smoke-tests that the auditor module loads and exposes the right flag."""

    def test_module_loads(self) -> None:
        from cortex.extensions.security import integrity_audit  # noqa: F401

    def test_rust_flag_consistent(self) -> None:
        from cortex.extensions.security.integrity_audit import _RUST_AVAILABLE as IA_RUST

        assert IA_RUST is _RUST_AVAILABLE
