"""Tests for Dimension 2: GEACL Consensus & Gossip Anti-Entropy."""

import asyncio
import pytest
from types import SimpleNamespace
from dataclasses import dataclass
import math

from cortex.thinking.fusion_models import ModelResponse, ThinkingHistory
from cortex.consensus.byzantine import WBFTConsensus
from cortex.ha.gossip import GossipProtocol
from cortex.consensus.geacl import GEACLCoordinator

@dataclass
class MockHistoryEntry:
    model: str
    win_rate: float
    
class MockThinkingHistory:
    def __init__(self, top_models_data):
        self._top = [MockHistoryEntry(m, w).__dict__ for m, w in top_models_data.items()]

    def top_models(self, limit):
        return self._top

def create_responses(contents_and_labels):
    return [
        ModelResponse(
            provider="mock",
            model=label,
            content=content,
            error=None,
            token_count=10,
            latency_ms=100.0,
        ) for label, content in contents_and_labels
    ]


# --- WBFT Tests ---

def test_wbft_domain_weights():
    """Verify domain-specific vote multipliers affect consensus."""
    responses = create_responses([
        ("model-A", "Here is the code structure"),
        ("model-B", "Here is the code structure"),
        ("model-C", "Completely different output"),
    ])
    
    # model-C is usually trusted (reputation 0.9), but domain weights give model-B 2.0x for 'code'
    domain_weights = {"code": {"mock:model-B": 2.0, "mock:model-A": 1.0, "mock:model-C": 1.0}}
    history = MockThinkingHistory({"mock:model-A": 0.5, "mock:model-B": 0.5, "mock:model-C": 0.9})
    
    wbft = WBFTConsensus(domain_weights=domain_weights, reputation_decay=1.0)
    verdict = wbft.evaluate(responses, history=history, domain="code")
    
    # Check that model-B has the 2.0x vote multiplier
    model_b_trust = next(t for t in verdict.all_assessments if t.response.label == "mock:model-B")
    assert model_b_trust.vote_multiplier == 2.0
    
    model_c_trust = next(t for t in verdict.all_assessments if t.response.label == "mock:model-C")
    assert model_c_trust.vote_multiplier == 1.0

def test_wbft_reputation_decay():
    """Verify historic reputation decays."""
    responses = create_responses([
        ("model-A", "output"),
    ])
    history = MockThinkingHistory({"mock:model-A": 1.0})
    wbft = WBFTConsensus(reputation_decay=0.8) # 80% decay applied
    
    verdict = wbft.evaluate(responses, history=history)
    trust = verdict.all_assessments[0]
    assert math.isclose(trust.reputation, 0.8)  # 1.0 * 0.8

# --- Gossip Tests ---

async def test_gossip_semantic_digests():
    """Verify semantic digest generation and comparison."""
    node1 = GossipProtocol("node1", peers=[])
    node1.update_state("test_key", {"data": "foo"})
    
    digest1 = node1.generate_digest()
    assert "test_key" in digest1.record_hashes
    assert digest1.vector_clock["node1"] == 1
    
    # Remote node with missing data
    node2 = GossipProtocol("node2", peers=[])
    keys_to_req, records_to_push = node1.receive_digest(node2.generate_digest())
    
    # Node1 should push test_key to Node2
    assert "test_key" in [r.key for r in records_to_push]
    assert keys_to_req == []

async def test_gossip_anti_entropy_resolution():
    """Verify vector clock / LWW resolution during anti-entropy."""
    node1 = GossipProtocol("node1", peers=[])
    node2 = GossipProtocol("node2", peers=[])
    
    # Node1 creates a version
    node1.update_state("keyA", {"ver": 1})
    rec1 = node1.get_state("keyA")
    
    # Node2 creates a slightly newer version later
    await asyncio.sleep(0.01)
    node2.update_state("keyA", {"ver": 2})
    rec2 = node2.get_state("keyA")
    
    # Both push to each other
    node1.receive_records([rec2])
    node2.receive_records([rec1])
    
    # Both should converge on Node2's version (higher version / newer timestamp)
    assert node1.get_state("keyA").value["ver"] == 2
    assert node2.get_state("keyA").value["ver"] == 2

# --- GEACL Tests ---

async def test_geacl_coordinator():
    """Verify GEACLCoordinator wraps WBFT and updates Gossip."""
    responses = create_responses([
        ("model-A", "Perfect implementation"),
        ("model-B", "Perfect implementation"),
    ])
    
    wbft = WBFTConsensus()
    gossip = GossipProtocol("node1", peers=[])
    geacl = GEACLCoordinator("node1", wbft, gossip)
    
    result = await geacl.propose_commit("task-alpha", "code", responses)
    
    assert result.success is True
    assert result.domain == "code"
    assert result.action_digest is not None
    
    # Verify it was persisted to Gossip state with the correct key convention
    state = gossip.get_state(f"geacl_commit_task-alpha_{hash('task-alpha')}")
    assert state is not None
    assert state.value["intent"] == "task-alpha"
    assert state.value["best_model"] in ("mock:model-A", "mock:model-B")
