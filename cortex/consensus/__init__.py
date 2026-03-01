"""
CORTEX v5.0 — Consensus Layer.

Provides immutable vote ledger, Merkle tree verification, Byzantine
fault tolerance for multi-model evaluation, and consensus management.
"""

from .byzantine import ByzantineVerdict, WBFTConsensus
from .manager import ConsensusManager
from .merkle import MerkleTree, compute_merkle_root, verify_merkle_proof
from .vote_ledger import ImmutableVoteLedger, VoteEntry

__all__ = [
    "ByzantineVerdict",
    "ConsensusManager",
    "ImmutableVoteLedger",
    "MerkleTree",
    "VoteEntry",
    "WBFTConsensus",
    "compute_merkle_root",
    "verify_merkle_proof",
]
