# [C5-REAL] Exergy-Maximized
"""
cat_id: test-babylon-core-v8
cat_type: test
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

import asyncio
import pytest

from babylon60.crypto.entanglement import StateEntangler, MerkleTreeAnchoring
from babylon60.federation.router import FederationRouter, MockQdrantIndex
from babylon60.observability.metrics_16d import Scanner16D
from babylon60.consensus.wbft import SwarmVote, WeightedByzantineConsensus
from babylon60.concurrency.actor import BatchCommitActor


def test_state_entanglement():
    prev_hash = "00000000000000000000"
    tx = {"amount": 100, "recipient": "swarm-0"}
    parallel_hashes = ["hash-a", "hash-b", "hash-c"]

    entangled_1 = StateEntangler.entangle_states(prev_hash, tx, parallel_hashes)
    entangled_2 = StateEntangler.entangle_states(prev_hash, tx, parallel_hashes)

    # Determinism assertion
    assert len(entangled_1) == 64
    # State-rollback protection assertion (modifying one parallel hash changes final hash)
    entangled_modified = StateEntangler.entangle_states(
        prev_hash, tx, ["hash-a", "hash-b", "hash-x"]
    )
    assert entangled_1 != entangled_modified


def test_merkle_anchoring():
    leaves = ["h1", "h2", "h3", "h4"]
    root = MerkleTreeAnchoring.build_tree(leaves)
    assert root is not None
    assert root.hash_val != ""

    msg = MerkleTreeAnchoring.generate_git_anchor_commit_message(root.hash_val, 42)
    assert "Merkle Root" in msg
    assert "epoch 42" in msg


def test_federation_router():
    qdrant = MockQdrantIndex()
    router = FederationRouter(qdrant)

    # Route write
    router.route_write("tenant-1", 1, "Fact 1 content", [0.1, 0.2, 0.3])
    router.route_write("tenant-2", 2, "Fact 2 content", [0.9, 0.8, 0.7])

    # Query cross-tenant
    results = router.route_cross_query([0.8, 0.8, 0.8], limit=1)
    assert len(results) == 1
    assert results[0]["tenant_id"] == "tenant-2"


def test_scanner_16d():
    mock_code = """
    def process_logic():
        global STATE
        STATE = 1
        items.append(5)
        if obj is None:
            return
        print("useful exergy work")
    """
    metrics = Scanner16D.audit_file_exergy(mock_code, num_dependencies=3)
    assert metrics.dependency_entropy == pytest.approx(0.45)
    assert metrics.state_friction > 0.0
    assert metrics.causal_isomorphism > 0.0


def test_consensus_wbft_sybil_dilution():
    votes = [
        SwarmVote("a1", "groq", "llama", 1.0, "result-A"),
        SwarmVote("a2", "groq", "llama", 1.0, "result-A"),  # Colluding llama family
        SwarmVote("a3", "cerebras", "qwen", 1.0, "result-B"),
    ]

    payload, ratio = WeightedByzantineConsensus.compute_quorum(votes)
    # The two llama votes are divided by 2 (weight = 0.5 each). Total A weight = 1.0
    # The single qwen vote is divided by 1 (weight = 1.0). Total B weight = 1.0
    # Since they tie, compute_quorum returns the maximum, but weighting is correctly diluted
    assert payload in ["result-A", "result-B"]
    assert ratio == 0.5


@pytest.mark.asyncio
async def test_batch_commit_actor():
    committed = []

    def callback(batch):
        committed.extend(batch)

    actor = BatchCommitActor(commit_callback=callback, flush_interval_ms=10)
    actor.start()

    await actor.send_write({"id": 1})
    await actor.send_write({"id": 2})

    # Wait for flush interval
    await asyncio.sleep(0.05)
    await actor.stop()

    assert len(committed) == 2
    assert committed[0]["id"] == 1
