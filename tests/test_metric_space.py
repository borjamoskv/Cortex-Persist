# [C5-REAL] Exergy-Maximized
"""
Verification tests for Metric Space Execution (Epoch 10).
"""

import pytest

from babylon60.engine.temporal.divergence import DivergenceMap
from babylon60.engine.meta.arbiter import MetaArbiter


def test_divergence_map_identical():
    """Test that identical trajectories have a distance of 0.0."""
    traj_a = [
        {"action": "init"},
        {"action": "read_file"},
        {"action": "write_file"},
    ]
    traj_b = [
        {"action": "init"},
        {"action": "read_file"},
        {"action": "write_file"},
    ]

    distance = DivergenceMap.compute_distance(traj_a, traj_b)
    assert distance == 0.0


def test_divergence_map_divergent():
    """Test that divergent trajectories yield > 0.0 distance."""
    traj_a = [
        {"action": "init"},
        {"action": "read_file"},
        {"action": "write_file"},
    ]
    traj_b = [
        {"action": "init"},
        {"action": "error"},
        {"action": "abort"},
    ]

    distance = DivergenceMap.compute_distance(traj_a, traj_b)
    assert distance > 0.0
    assert distance <= 1.0


def test_meta_arbiter_collapse_topology():
    """Test that MetaArbiter selects the consensus trajectory."""
    # Three agents run a task. Two agree, one hallucinates.
    traj_consensus_1 = [
        {"action": "init"},
        {"action": "read_file"},
        {"action": "write_file"},
    ]
    traj_consensus_2 = [
        {"action": "init"},
        {"action": "read_file"},
        {"action": "write_file"},
    ]
    traj_hallucination = [
        {"action": "init"},
        {"action": "read_file"},
        {"action": "delete_all"},
        {"action": "abort"},
    ]

    trajectories = [traj_hallucination, traj_consensus_1, traj_consensus_2]

    canonical = MetaArbiter.collapse_topology(trajectories)

    # The arbiter should collapse to the consensus trajectory
    assert canonical == traj_consensus_1
