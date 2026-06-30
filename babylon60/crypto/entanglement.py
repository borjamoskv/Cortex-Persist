# [C5-REAL] Exergy-Maximized
"""
cat_id: crypto-entanglement
cat_type: module
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

import hashlib
import json
import time
from typing import Any


class MerkleNode:
    def __init__(self, left: "MerkleNode | None" = None, right: "MerkleNode | None" = None, hash_val: str = ""):
        self.left = left
        self.right = right
        self.hash_val = hash_val


def calculate_sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class StateEntangler:
    """Provides cryptographic state entanglement (INV-E01).
    Ensures state-rollback protection by forcing the transaction hash
    to entangle with parallel active agents' state hashes.
    """

    @staticmethod
    def entangle_states(
        previous_hash: str,
        transaction_data: dict[str, Any],
        parallel_state_hashes: list[str],
    ) -> str:
        """Computes an entangled hash linking the transaction data to parallel agents."""
        sorted_parallel = sorted(parallel_state_hashes)
        parallel_seed = calculate_sha256(json.dumps(sorted_parallel, sort_keys=True))
        
        payload = {
            "previous_hash": previous_hash,
            "tx": transaction_data,
            "parallel_seed": parallel_seed,
            "entropy_salt": f"{time.monotonic()}",
        }
        raw_payload = json.dumps(payload, sort_keys=True)
        return calculate_sha256(raw_payload)


class MerkleTreeAnchoring:
    """Constructs Merkle Trees from transaction hashes and outputs publication anchors."""

    @staticmethod
    def build_tree(leaves: list[str]) -> MerkleNode | None:
        if not leaves:
            return None
        
        nodes = [MerkleNode(hash_val=h) for h in leaves]
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                    parent_hash = calculate_sha256(left.hash_val + right.hash_val)
                    next_level.append(MerkleNode(left=left, right=right, hash_val=parent_hash))
                else:
                    next_level.append(left)
            nodes = next_level
        return nodes[0]

    @staticmethod
    def generate_git_anchor_commit_message(root_hash: str, epoch: int) -> str:
        """Formats the anchor message for Git Sentinel publishing (Axiom 2 / C7 Proof-of-Publication)."""
        return f"[bridge] publish(anchor): Merkle Root {root_hash} for epoch {epoch} [C5-REAL]"
