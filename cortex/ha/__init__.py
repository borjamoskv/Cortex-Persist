"""
CORTEX v4.0 — High Availability Layer.

Provides Raft consensus, CRDTs, and Gossip protocols for multi-node clusters.
"""

from .crdt import LWWRegister, VectorClock
from .gossip import GossipProtocol
from .raft import NodeRole, RaftNode
