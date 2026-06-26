# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MerkleNode:
    """A node within the Merkle Tree (V8 Immutable)."""

    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None
    is_leaf: bool = False


class MerkleTree:
    """High-performance Merkle Tree for batch transaction verification."""

    def __init__(self, leaves: list[str]):
        if not leaves:
            self.root = None
            self._leaves = []
            return

        self._leaves = leaves
        nodes = [MerkleNode(hash=h, is_leaf=True) for h in leaves]
        self.layers = []
        self.root = self._build_recursive(nodes)

    def _hash_pair(self, left: str, right: str) -> str:
        return hashlib.sha256((left + right).encode()).hexdigest()

    def _build_recursive(self, nodes: list[MerkleNode]) -> MerkleNode:
        self.layers.append(nodes)
        if len(nodes) == 1:
            return nodes[0]

        next_layer = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            combined_hash = self._hash_pair(left.hash, right.hash)
            next_layer.append(MerkleNode(hash=combined_hash, left=left, right=right))

        return self._build_recursive(next_layer)

    @property
    def root_hash(self) -> str | None:
        return self.root.hash if self.root else None

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """Optimized path discovery (O(log N)) using the pre-built Merkle Tree structure."""
        if not self.root or not (0 <= index < len(self._leaves)):
            return []

        proof = []
        idx = index
        # We skip the last layer since it only contains the root
        for layer in self.layers[:-1]:
            sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if sibling_idx < len(layer):
                proof.append((layer[sibling_idx].hash, "R" if idx % 2 == 0 else "L"))
            else:
                # Duplication case
                proof.append((layer[idx].hash, "R"))
            idx //= 2
        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[tuple[str, str]], root_hash: str) -> bool:
        current = leaf_hash
        for sibling_hash, direction in proof:
            if direction == "L":
                current = hashlib.sha256((sibling_hash + current).encode()).hexdigest()
            else:
                current = hashlib.sha256((current + sibling_hash).encode()).hexdigest()
        return current == root_hash


class SemanticMerkleTree:
    """Vectorial Merkle Tree - Validates integrity using semantic distance.

    Instead of comparing SHA-256 hashes of raw bytes, this tree compares
    the cosine similarity of embedding vectors. A paraphrased memory
    ("likes apples" → "prefers apples") passes validation at threshold 0.98,
    while a genuine hallucination ("likes apples" → "likes pears") fails.

    GPU-native: batch-generates fingerprints using CUDA when available.
    Edge-compatible: cosine comparison is O(D) with D=384, no deps.
    """

    def __init__(
        self,
        contents: list[str],
        embedder: Any = None,
        threshold: float = 0.98,
    ):
        from cortex.engine.uncategorized.semantic_hash import (
            SemanticFingerprint,
            batch_fingerprint,
        )

        self.threshold = threshold
        self._contents = contents

        if not contents:
            self.root = None
            self._fingerprints: list[SemanticFingerprint] = []
            self._classic_tree = None
            return

        # GPU-accelerated batch embedding
        self._fingerprints = batch_fingerprint(contents, embedder)

        # Build classic Merkle Tree from fingerprint hashes for O(log N) proofs
        leaf_hashes = [fp.hash for fp in self._fingerprints]
        self._classic_tree = MerkleTree(leaf_hashes)
        self.root = self._classic_tree.root

    @property
    def root_hash(self) -> str | None:
        return self._classic_tree.root_hash if self._classic_tree else None

    def verify_content(self, index: int, content: str, embedder: Any = None) -> dict:
        """Verify a single content entry against the tree using semantic distance.

        Returns a dict with:
          - valid: bool (passes semantic threshold)
          - similarity: float (cosine similarity)
          - exact_match: bool (byte-exact hash match)
          - threshold: float
        """
        from cortex.engine.uncategorized.semantic_hash import (
            cosine_similarity,
            semantic_fingerprint,
        )

        if not self._fingerprints or not (0 <= index < len(self._fingerprints)):
            return {
                "valid": False,
                "similarity": 0.0,
                "exact_match": False,
                "threshold": self.threshold,
                "error": "index_out_of_range",
            }

        stored_fp = self._fingerprints[index]
        current_fp = semantic_fingerprint(content, embedder)

        sim = cosine_similarity(stored_fp.embedding, current_fp.embedding)
        exact = stored_fp.hash == current_fp.hash

        return {
            "valid": sim >= self.threshold,
            "similarity": round(sim, 6),
            "exact_match": exact,
            "threshold": self.threshold,
        }

    def verify_batch(self, contents: list[str], embedder: Any = None) -> list[dict]:
        """Verify multiple content entries. GPU-accelerated via batch embedding."""
        from cortex.engine.uncategorized.semantic_hash import batch_fingerprint, cosine_similarity

        if not self._fingerprints:
            return []

        current_fps = batch_fingerprint(contents, embedder)
        results = []

        for i, (stored_fp, current_fp) in enumerate(
            zip(self._fingerprints, current_fps, strict=True)
        ):
            sim = cosine_similarity(stored_fp.embedding, current_fp.embedding)
            exact = stored_fp.hash == current_fp.hash
            results.append(
                {
                    "index": i,
                    "valid": sim >= self.threshold,
                    "similarity": round(sim, 6),
                    "exact_match": exact,
                    "threshold": self.threshold,
                }
            )

        return results
