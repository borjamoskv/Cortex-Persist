# [C5-REAL] Exergy-Maximized
"""
High Availability Layer.

Provides Raft consensus, CRDTs, and Gossip protocols for multi-node clusters.
"""

from .crdt import LWWRegister, VectorClock
from .gossip import GossipProtocol
from .raft import NodeRole, RaftNode

__all__ = [
    "GossipProtocol",
    "LWWRegister",
    "NodeRole",
    "RaftNode",
    "VectorClock",
]
