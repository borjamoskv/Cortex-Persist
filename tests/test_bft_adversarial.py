# [C5-REAL] Exergy-Maximized
"""
Adversarial stress tests for BFT QuorumGateway consensus.
Reality Level: C5-REAL
"""

import pytest
import asyncio
import json
import base64
import time
from unittest.mock import MagicMock, patch

from babylon60.swarm.auth_gateway import QuorumGateway
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


class MockEngine:
    def __init__(self):
        import sqlite3

        self.pool = MagicMock()
        self.conn = sqlite3.connect(":memory:")
        self.pool.get_connection.return_value = self.conn


def generate_agent_keys():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return private_key, base64.b64encode(pub_bytes).decode("utf-8")


def sign_payload(private_key, payload: str, fact_hash: str) -> str:
    import hashlib

    content_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    message = f"{content_digest}:{fact_hash}".encode()
    signature = private_key.sign(message)
    return base64.b64encode(signature).decode("utf-8")


@pytest.mark.asyncio
async def test_byzantine_minority_cannot_override():
    """f < n/3 Byzantine nodes cannot corrupt consensus and force override."""
    engine = MockEngine()
    # n=4, f=1 (threshold is 3)
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    agents = [generate_agent_keys() for _ in range(4)]

    # Corrupt/malicious proposal
    payload = {"action": "wipe_entire_database", "danger": True}
    req_id = await gateway.request_override("Malicious Payload", payload)
    payload_str = json.dumps(payload)

    # Only the Byzantine agent (Agent 3) votes YES (semantic_truth=True)
    sig3 = sign_payload(agents[3][0], payload_str, req_id)
    success = await gateway.submit_vote(req_id, sig3, agents[3][1], semantic_truth=True)
    assert success is True

    # Honest agents 0, 1, 2 evaluate the payload and withhold votes (semantic_truth=False)
    for i in range(3):
        sig = sign_payload(agents[i][0], payload_str, req_id)
        success = await gateway.submit_vote(req_id, sig, agents[i][1], semantic_truth=False)
        assert success is False

    # Verify status remains PENDING and consensus is NOT reached
    cursor = engine.conn.cursor()
    cursor.execute("SELECT status, signatures_json FROM quorum_requests WHERE id = ?", (req_id,))
    status, sigs = cursor.fetchone()
    assert status == "PENDING"
    assert len(json.loads(sigs)) == 1  # Only Byzantine node's vote registered


@pytest.mark.asyncio
async def test_replay_attack_rejected():
    """Duplicate signed votes from the same agent public key are rejected."""
    engine = MockEngine()
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    agents = [generate_agent_keys() for _ in range(4)]

    payload = {"action": "deploy_agent", "id": "agent-x"}
    req_id = await gateway.request_override("Honest Deployment", payload)
    payload_str = json.dumps(payload)

    # First vote from agent 0 succeeds
    sig0 = sign_payload(agents[0][0], payload_str, req_id)
    success = await gateway.submit_vote(req_id, sig0, agents[0][1], semantic_truth=True)
    assert success is True

    # Replay same vote signature and public key
    dup_success = await gateway.submit_vote(req_id, sig0, agents[0][1], semantic_truth=True)
    assert dup_success is False

    # Check vote count remains 1
    cursor = engine.conn.cursor()
    cursor.execute("SELECT signatures_json FROM quorum_requests WHERE id = ?", (req_id,))
    sigs = json.loads(cursor.fetchone()[0])
    assert len(sigs) == 1


@pytest.mark.asyncio
async def test_quorum_timeout_fails_gracefully():
    """Incomplete quorum within timeout returns failure and marks status."""
    engine = MockEngine()
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    payload = {"action": "scale_up"}
    req_id = await gateway.request_override("Scale Operation", payload)

    # Initially, request is not timed out
    is_timed_out = await gateway.check_timeout(req_id, timeout_s=10.0)
    assert is_timed_out is False

    # Mock time.monotonic to simulate 11 seconds passing
    current_time = time.monotonic()
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = current_time + 11.0
        is_timed_out = await gateway.check_timeout(req_id, timeout_s=10.0)
        assert is_timed_out is True

    # Verify status in database transitioned to TIMEOUT_EXPIRED
    cursor = engine.conn.cursor()
    cursor.execute("SELECT status FROM quorum_requests WHERE id = ?", (req_id,))
    status = cursor.fetchone()[0]
    assert status == "TIMEOUT_EXPIRED"


@pytest.mark.asyncio
async def test_concurrent_proposals_resolved():
    """Parallel proposals resolve without deadlock or collision."""
    engine = MockEngine()
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    agents = [generate_agent_keys() for _ in range(4)]
    payload = {"action": "noop"}
    payload_str = json.dumps(payload)

    async def run_single_proposal(idx: int):
        req_id = await gateway.request_override(f"Proposal-{idx}", payload)

        # Honest nodes submit votes
        v0 = await gateway.submit_vote(
            req_id, sign_payload(agents[0][0], payload_str, req_id), agents[0][1]
        )
        v1 = await gateway.submit_vote(
            req_id, sign_payload(agents[1][0], payload_str, req_id), agents[1][1]
        )
        v2 = await gateway.submit_vote(
            req_id, sign_payload(agents[2][0], payload_str, req_id), agents[2][1]
        )

        assert v0 and v1 and v2

        cursor = engine.conn.cursor()
        cursor.execute("SELECT status FROM quorum_requests WHERE id = ?", (req_id,))
        assert cursor.fetchone()[0] == "QUORUM_REACHED"

    # Issue 10 proposals concurrently
    await asyncio.gather(*(run_single_proposal(i) for i in range(10)))

@pytest.mark.asyncio
async def test_network_partition_convergence_time():
    """Simulates a network partition (async delay) to check convergence time."""
    engine = MockEngine()
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    agents = [generate_agent_keys() for _ in range(4)]
    payload = {"action": "partition_test"}
    payload_str = json.dumps(payload)
    req_id = await gateway.request_override("Partition Payload", payload)

    start_time = time.monotonic()

    # Agent 0 and 1 are fast, agent 2 is delayed (partitioned)
    v0 = await gateway.submit_vote(
        req_id, sign_payload(agents[0][0], payload_str, req_id), agents[0][1]
    )
    v1 = await gateway.submit_vote(
        req_id, sign_payload(agents[1][0], payload_str, req_id), agents[1][1]
    )
    assert v0 and v1

    # Still not reached quorum (2/3 needed for f=1 and n=4, wait, quorum is 2f+1 = 3)
    cursor = engine.conn.cursor()
    cursor.execute("SELECT status FROM quorum_requests WHERE id = ?", (req_id,))
    assert cursor.fetchone()[0] == "PENDING"

    # Simulate delay for agent 2
    delay_time = 0.2
    await asyncio.sleep(delay_time)
    
    v2 = await gateway.submit_vote(
        req_id, sign_payload(agents[2][0], payload_str, req_id), agents[2][1]
    )
    assert v2

    # Now quorum is reached
    cursor.execute("SELECT status FROM quorum_requests WHERE id = ?", (req_id,))
    assert cursor.fetchone()[0] == "QUORUM_REACHED"

    end_time = time.monotonic()
    assert (end_time - start_time) >= delay_time
