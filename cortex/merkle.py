"""
CORTEX v4.1 — Merkle Tree Implementation.
Standard Merkle Tree for cryptographic verification of transactions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class MerkleNode:
    """A node in the Merkle Tree."""

    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None
    is_leaf: bool = False


class MerkleTree:
    """
    Merkle tree for batch transaction verification.
    """

    def __init__(self, leaves: list[str]):
        """
        Build a Merkle tree from leaf hashes.
        """
        if not leaves:
            self.leaves = []
            self.root = None
            return

        self.leaves = leaves
        self.root = self._build_tree([MerkleNode(h, is_leaf=True) for h in leaves])

    def _hash_pair(self, left: str, right: str) -> str:
        """Hash two child hashes together."""
        combined = left + right
        return hashlib.sha256(combined.encode()).hexdigest()

    def _build_tree(self, nodes: list[MerkleNode]) -> MerkleNode:
        """Recursively build the tree bottom-up."""
        if not nodes:
            raise ValueError("Nodes list cannot be empty")
        if len(nodes) == 1:
            return nodes[0]

        next_level = []
        # Process in pairs
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            # Use same node if odd count (duplicate right sibling)
            right = nodes[i + 1] if i + 1 < len(nodes) else left

            next_level.append(
                MerkleNode(hash=self._hash_pair(left.hash, right.hash), left=left, right=right)
            )

        return self._build_tree(next_level)

    def get_root(self) -> str | None:
        """Get the root hash of the tree."""
        return self.root.hash if self.root else None

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """Get a Merkle proof for a leaf at the given index."""
        if not self.root or index < 0 or index >= len(self.leaves):
            return []

        proof: list[tuple[str, str]] = []
        current_level = [MerkleNode(h, is_leaf=True) for h in self.leaves]
        curr_idx = index

        while len(current_level) > 1:
            # Determine sibling
            is_right_child = curr_idx % 2 == 1
            sibling_idx = curr_idx - 1 if is_right_child else curr_idx + 1

            if sibling_idx < len(current_level):
                sibling_hash = current_level[sibling_idx].hash
                proof.append((sibling_hash, "L" if is_right_child else "R"))
            else:
                # Odd node count, sibling is itself (right=left)
                proof.append((current_level[curr_idx].hash, "R"))

            # Move to next level
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                r = current_level[i + 1] if i + 1 < len(current_level) else left
                next_level.append(
                    MerkleNode(hash=self._hash_pair(left.hash, r.hash), left=left, right=r)
                )

            current_level = next_level
            curr_idx //= 2

        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[tuple[str, str]], root: str) -> bool:
        """Verify a Merkle proof against a root hash."""
        current = leaf_hash
        for sibling, direction in proof:
            if direction == "L":
                combined = sibling + current
            else:
                combined = current + sibling
            current = hashlib.sha256(combined.encode()).hexdigest()
        return current == root
