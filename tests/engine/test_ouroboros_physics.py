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
    consolidate_retrieval_graph,
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
    consolidate_retrieval_graph(target_node, db, now=now)
    
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
        consolidate_retrieval_graph(node, db, now=now)
        
    final_node = db.get_node("N_ISOLATED")
    assert final_node.kinetic_mass <= MAX_KINETIC_MULTIPLIER
    assert final_node.kinetic_mass > 1.0
    
    # With 100 boosts of 0.15, it would reach 15.0 if unchecked. 
    # MAX_KINETIC_MULTIPLIER is 2.0.
    assert final_node.kinetic_mass == pytest.approx(MAX_KINETIC_MULTIPLIER)


def test_commutativity_of_independent_injections():
    """
    Test de Invarianza ante Reordenamiento (CRÍTICO).
    f(a → b) == f(b → a) cuando no hay dependencia causal directa.
    """
    now = time.time()
    
    def run_sequence(order: List[str]) -> Dict[str, float]:
        db = MockGraphDB()
        node_c = FactNode(node_id="C", created_at=now, last_accessed_at=now, origin_type="verified_commit")
        node_a = FactNode(node_id="A", created_at=now, last_accessed_at=now, origin_type="verified_commit")
        node_b = FactNode(node_id="B", created_at=now, last_accessed_at=now, origin_type="verified_commit")
        
        db.add_node(node_c, [])
        db.add_node(node_a, ["C"])
        db.add_node(node_b, ["C"])
        
        for n in order:
            consolidate_retrieval_graph(db.get_node(n), db, now=now)
            
        return {
            "A": db.get_node("A").kinetic_mass,
            "B": db.get_node("B").kinetic_mass,
            "C": db.get_node("C").kinetic_mass,
        }
        
    seq1 = run_sequence(["A", "B"])
    seq2 = run_sequence(["B", "A"])
    
    assert seq1["A"] == pytest.approx(seq2["A"])
    assert seq1["B"] == pytest.approx(seq2["B"])
    assert seq1["C"] == pytest.approx(seq2["C"])


def test_partial_conservation():
    """
    Test de Conservación Parcial (No creación ex nihilo).
    sum(E_after) <= sum(E_before) + injected_energy
    """
    db = MockGraphDB()
    now = time.time()
    
    node0 = FactNode(node_id="N0", created_at=now, last_accessed_at=now, origin_type="verified_commit")
    node1 = FactNode(node_id="N1", created_at=now, last_accessed_at=now, origin_type="verified_commit")
    node2 = FactNode(node_id="N2", created_at=now, last_accessed_at=now, origin_type="verified_commit")
    
    db.add_node(node0, [])
    db.add_node(node1, ["N0"])
    db.add_node(node2, ["N1"])
    
    initial_sum = node0.kinetic_mass + node1.kinetic_mass + node2.kinetic_mass
    
    consolidate_retrieval_graph(node2, db, now=now)
    
    final_sum = db.get_node("N0").kinetic_mass + db.get_node("N1").kinetic_mass + db.get_node("N2").kinetic_mass
    delta_sum = final_sum - initial_sum
    
    max_theoretical_injection = HEBBIAN_BOOST_PER_ACCESS * (1 - 0.85**3) / (1 - 0.85)
    
    assert delta_sum == pytest.approx(max_theoretical_injection)
    assert delta_sum <= (HEBBIAN_BOOST_PER_ACCESS / (1 - 0.85))


def test_deep_limit_stability():
    """
    Test de Límite Profundo (d → grande).
    Verifica que E(d) ≈ 0 y que no hay underflow extraño ni acumulación flotante residual.
    """
    db = MockGraphDB()
    now = time.time()
    
    for i in range(100):
        node = FactNode(
            node_id=f"N{i}",
            created_at=now,
            last_accessed_at=now,
            origin_type="verified_commit"
        )
        ancestors = [f"N{i-1}"] if i > 0 else []
        db.add_node(node, ancestors)
        
    initial_mass_n0 = db.get_node("N0").kinetic_mass
    
    consolidate_retrieval_graph(db.get_node("N99"), db, now=now, max_depth=150)
    
    delta = db.get_node("N0").kinetic_mass - initial_mass_n0
    
    # Con d=99, la inyección debe ser E0 * 0.85^99 = 0.15 * 1.02e-7 ≈ 1.5e-8
    # Comprobamos que es estable sin underflow extremo ni acumulación rara.
    expected_delta = HEBBIAN_BOOST_PER_ACCESS * (0.85 ** 99)
    
    assert delta == pytest.approx(expected_delta, rel=1e-5)
    assert delta < 1e-7
    assert delta > 0.0
