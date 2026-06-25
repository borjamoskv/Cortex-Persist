from cortex.guards.epistemic_guard import EpistemicGuard
from cortex.types.epistemics import (
    ObservationNode,
    InferenceNode,
    ConsensusNode,
)

def test_guard_accepts_valid_observation():
    node = ObservationNode(content="System started", sensor_id="syslog")
    result = EpistemicGuard.validate_node(node, "Persist-Executor", {})
    assert result is None

def test_guard_rejects_invalid_certainty_observation():
    node = ObservationNode(content="System started", sensor_id="syslog")
    node.certainty = "C3" # Manually force invalid certainty for test
    result = EpistemicGuard.validate_node(node, "Persist-Executor", {})
    assert result is not None
    assert result["accepted"] is False
    assert result["code"] == "INVALID_CERTAINTY"

def test_guard_accepts_valid_inference():
    node = InferenceNode(content="Therefore, A=B", source_node_ids=["node_1", "node_2"])
    result = EpistemicGuard.validate_node(node, "Omega-Prime", {})
    assert result is None

def test_guard_rejects_orphan_inference():
    node = InferenceNode(content="Therefore, A=B", source_node_ids=["temp"])
    node.source_node_ids = [] # Force orphan state
    result = EpistemicGuard.validate_node(node, "Omega-Prime", {})
    assert result is not None
    assert result["accepted"] is False
    assert result["code"] == "ORPHAN_INFERENCE"

def test_guard_accepts_valid_consensus_from_guardian():
    node = ConsensusNode(content="Quorum reached on A", quorum_score=0.9, voter_ids=["v1", "v2", "v3"])
    result = EpistemicGuard.validate_node(node, "WBFT-Router", {})
    assert result is None

def test_guard_rejects_consensus_forgery():
    node = ConsensusNode(content="Quorum reached on A", quorum_score=0.9, voter_ids=["v1", "v2", "v3"])
    result = EpistemicGuard.validate_node(node, "AETHER-1", {}) # Not authorized
    assert result is not None
    assert result["accepted"] is False
    assert result["code"] == "EPISTEMIC_FORGERY"
