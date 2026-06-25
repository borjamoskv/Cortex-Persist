import pytest
from pydantic import ValidationError
from legacy_research.types.epistemics import (
    ObservationNode,
    InferenceNode,
    ConsensusNode,
    SimulationNode,
    CounterfactualNode,
    BeliefNode,
)

def test_observation_node_valid():
    node = ObservationNode(content="User logged in", sensor_id="auth_service")
    assert node.type == "observation"
    assert node.certainty == "C5"
    assert node.content == "User logged in"
    assert node.sensor_id == "auth_service"

def test_inference_node_requires_source():
    with pytest.raises(ValidationError):
        # Missing source_node_ids
        InferenceNode(content="User must be active")
        
    node = InferenceNode(content="User must be active", source_node_ids=["obs_123"])
    assert node.type == "inference"
    assert node.certainty == "C3"
    assert node.source_node_ids == ["obs_123"]

def test_consensus_node_requires_quorum_and_voters():
    with pytest.raises(ValidationError):
        # Missing quorum_score and voter_ids
        ConsensusNode(content="System is stable")
        
    with pytest.raises(ValidationError):
        # Not enough voters (requires >= 3)
        ConsensusNode(content="System is stable", quorum_score=1.0, voter_ids=["v1", "v2"])
        
    node = ConsensusNode(content="System is stable", quorum_score=0.9, voter_ids=["v1", "v2", "v3"])
    assert node.type == "consensus"
    assert node.certainty == "C5"
    assert node.quorum_score == 0.9
    assert len(node.voter_ids) == 3

def test_simulation_node_valid():
    node = SimulationNode(content="What if DB goes down?", branch_id="sim_456")
    assert node.type == "simulation"
    assert node.certainty == "C2"
    assert node.branch_id == "sim_456"

def test_counterfactual_node_valid():
    node = CounterfactualNode(content="Adversary compromised token", divergence_node_id="node_789")
    assert node.type == "counterfactual"
    assert node.certainty == "C1"
    assert node.divergence_node_id == "node_789"

def test_belief_node_valid():
    node = BeliefNode(content="I think the user is an admin", agent_id="agent_007")
    assert node.type == "belief"
    assert node.certainty == "C3"
    assert node.agent_id == "agent_007"
