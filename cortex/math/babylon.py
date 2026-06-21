import hashlib
from typing import List, Tuple, Sequence

class Babylon60Vector:
    """
    [DEPRECATED - BABYLON-60 Phase 4]
    Spatial vectors maintain a Euclidean illusion. This will be entirely removed
    in favor of EpistemicTrajectory DAG mapping.
    """
    def __init__(self, data: List[int]):
        for val in data:
            if not isinstance(val, int):
                raise ValueError(f"BABYLON-60 violation: Non-integer scalar detected in vector. Type: {type(val)}")
        self.data = tuple(data)
        
    def __len__(self) -> int:
        return len(self.data)
        
    def __getitem__(self, idx: int) -> int:
        return self.data[idx]

def manhattan_distance(a: Babylon60Vector, b: Babylon60Vector) -> int:
    """
    [DEPRECATED - BABYLON-60 Phase 4]
    Calculates L1 Manhattan distance. Spatial metrics are replaced by causal overlaps.
    """
    if len(a) != len(b):
        raise ValueError("Vector dimension mismatch.")
    return sum(abs(x - y) for x, y in zip(a.data, b.data))

class EpistemicTrajectory:
    """
    BABYLON-60 C5-REAL Representation: Content Addressed Cognition.
    A node is not a point in space; it is a trajectory in a causal graph.
    """
    def __init__(self, node_hash: str, ancestry_hashes: set[str], witness_hashes: set[str]):
        self.node_hash = node_hash
        self.ancestry_hashes = frozenset(ancestry_hashes)
        self.witness_hashes = frozenset(witness_hashes)

def causal_distance(ancestry_overlap: int, ledger_overlap: int, witness_overlap: int, temporal_overlap: int) -> int:
    """
    Calculates the absolute Epistemological Distance between two cognitive nodes.
    Distance represents structural divergence in their causal history, not spatial separation.
    
    Returns:
        int: uint16 range causal divergence (0 = identical lineage, >0 = divergent)
    """
    # Base 60 Babylonian constants for causal weighting
    ANCESTRY_WEIGHT = 60
    WITNESS_WEIGHT = 30
    LEDGER_WEIGHT = 10
    TEMPORAL_WEIGHT = 1

    # Base divergence starts at an upper bound (e.g. 1000 or scaled max)
    # The higher the overlap in causal history, the shorter the "distance".
    max_divergence = 1000
    
    score = (
        (ancestry_overlap * ANCESTRY_WEIGHT) +
        (witness_overlap * WITNESS_WEIGHT) +
        (ledger_overlap * LEDGER_WEIGHT) +
        (temporal_overlap * TEMPORAL_WEIGHT)
    )
    
    distance = max(0, max_divergence - score)
    # Clamp to uint16 (0 - 65535)
    return min(distance, 65535)

def hash_distance_rollup(root_hash: str, distance_batch: Sequence[Tuple[str, str, int]]) -> str:
    """
    Merkle Cognition Tree: Rollup Batch Hashing.
    Prevents Merkle Storms by batching multiple causal distance calculations
    into a single determinist root hash update for the Ledger.
    """
    m = hashlib.sha256()
    m.update(root_hash.encode('utf-8'))
    for q_hash, t_hash, dist in distance_batch:
        payload = f"{q_hash}:{t_hash}:{dist}"
        m.update(payload.encode('utf-8'))
    return m.hexdigest()
