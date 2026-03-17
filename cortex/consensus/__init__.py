"""
CORTEX v5.0 — Consensus Layer.

Provides immutable vote ledger, Merkle tree verification, and consensus protocols.
"""

from .merkle import MerkleTree, compute_merkle_root, verify_merkle_proof
from .rwa_bft import AgentVote, ConsensusResult, RWABFTConsensus, VoteOutcome
<<<<<<< HEAD
from .vote_ledger import ImmutableVoteLedger
=======
from .vote_ledger import ImmutableVoteLedger, VoteEntry
>>>>>>> origin/main

__all__ = [
    "MerkleTree",
    "compute_merkle_root",
    "verify_merkle_proof",
    "ImmutableVoteLedger",
<<<<<<< HEAD
=======
    "VoteEntry",
>>>>>>> origin/main
    # RWA-BFT
    "RWABFTConsensus",
    "AgentVote",
    "VoteOutcome",
    "ConsensusResult",
]
