from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MerkleNode:
    """A node in the Merkle Tree representing a cryptographic hash."""

    def __init__(
        self,
        left: MerkleNode | None = None,
        right: MerkleNode | None = None,
        hash_val: str | None = None,
    ):
        self.left = left
        self.right = right
        self.hash: str = hash_val or self._compute_hash()

    def _compute_hash(self) -> str:
        left_h = self.left.hash if self.left else ""
        right_h = self.right.hash if self.right else ""
        data = left_h + right_h
        return hashlib.sha256(data.encode()).hexdigest()


class MerkleTree:
    """A balanced Merkle Tree for transaction integrity (Ω-Architecture)."""

    def __init__(self, leaves: list[str]):
        if not leaves:
            self.root: MerkleNode | None = None
            return

        nodes = [MerkleNode(hash_val=leaf) for leaf in leaves]
        while len(nodes) > 1:
            if len(nodes) % 2 != 0:
                nodes.append(nodes[-1])
            new_level = []
            for i in range(0, len(nodes), 2):
                new_level.append(MerkleNode(left=nodes[i], right=nodes[i + 1]))
            nodes = new_level
        self.root = nodes[0]

    @property
    def root_hash(self) -> str | None:
        return self.root.hash if self.root else None


class SemanticMerkleTree(MerkleTree):
    """A Merkle Tree that uses semantic content hashing for data integrity."""

    def __init__(self, data_list: list[Any]):
        leaves = [self._semantic_hash(data) for data in data_list]
        super().__init__(leaves)

    def _semantic_hash(self, data: Any) -> str:
        # Stable JSON serialization for consistent hashing
        serializable = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serializable.encode()).hexdigest()
