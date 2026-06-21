# [C5-REAL] Exergy-Maximized
"""
Ouroboros Physics Tests
Validates strict monotonic attenuation and cumulative stability of Hebbian Reinforcement.
"""

import time
import pytest
from typing import Dict, List

from scripts.ouroboros_prune import (
    FactNode,
    hebbian_reinforce,
    consolidate_epistemic_graph,
    MAX_KINETIC_MULTIPLIER,
    HEBBIAN_BOOST_PER_ACCESS
)

class MockGraphDB:
    def __init__(self):
        self.nodes: Dict[str, FactNode] = {}
        self.edges: Dict[str, List[str]] = {}

    def get_node(self, node_id: str) -> FactNode:
        return self.nodes[node_id]

    def update_node(self, node: FactNode) -> None:
        self.nodes[node.node_id] = node

    def get_ancestors(self, node_id: str) -> List[str]:
        return self.edges.get(node_id, [])

    def add_node(self, node: FactNode, ancestors: List[str] = None):
        self.nodes[node.node_id] = node
        self.edges[node.node_id] = ancestors or []


def test_strict_monotonic_attenuation():
    """
    Constructs a linear causal chain: N0 <- N1 <- N2 <- N3 <- N4 <- N5
    Triggering from N5 should strictly decay backwards.
    """
    db = MockGraphDB()
    now = time.time()
    
    # Create N0 to N5
    for i in range(6):
        node = FactNode(
            node_id=f"N{i}",
            created_at=now,
            last_accessed_at=now,
            origin_type="verified_commit"  # hebbiano_eligible = True
        )
        ancestors = [f"N{i-1}"] if i > 0 else []
        db.add_node(node, ancestors)
        
    target_node = db.get_node("N5")
    
    # Store initial kinetic masses
    initial_masses = {f"N{i}": db.get_node(f"N{i}").kinetic_mass for i in range(6)}
    
    # Consolidate
    consolidate_epistemic_graph(target_node, db, now=now)
    
    deltas = []
    # Depth from N5 to N0 goes from 0 to 5
    for i in range(5, -1, -1):
        depth = 5 - i
        new_mass = db.get_node(f"N{i}").kinetic_mass
        delta = new_mass - initial_masses[f"N{i}"]
        deltas.append(delta)
        
        # Verify E(d) = E0 * 0.85^d
        expected_delta = HEBBIAN_BOOST_PER_ACCESS * (0.85 ** depth)
        assert abs(delta - expected_delta) < 1e-6, f"Mismatch at depth {depth}: {delta} != {expected_delta}"

    # Verify strict monotonicity
    for i in range(len(deltas) - 1):
        assert deltas[i] > deltas[i+1], f"Monotonicity failed between depth {i} and {i+1}"


def test_cumulative_stability_limit():
    """
    Tests that 100 consecutive reinforcements on the same node do not exceed MAX_KINETIC_MULTIPLIER.
    """
    db = MockGraphDB()
    now = time.time()
    
    node = FactNode(
        node_id="N_ISOLATED",
        created_at=now,
        last_accessed_at=now,
        origin_type="verified_commit"
    )
    db.add_node(node, [])
    
    for _ in range(100):
        consolidate_epistemic_graph(node, db, now=now)
        
    final_node = db.get_node("N_ISOLATED")
    assert final_node.kinetic_mass <= MAX_KINETIC_MULTIPLIER
    assert final_node.kinetic_mass > 1.0
    
    # With 100 boosts of 0.15, it would reach 15.0 if unchecked. 
    # MAX_KINETIC_MULTIPLIER is 2.0.
    assert final_node.kinetic_mass == pytest.approx(MAX_KINETIC_MULTIPLIER)
