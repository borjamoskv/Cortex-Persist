# [C5-REAL] Exergy-Maximized
import pytest
import asyncio
import json
from unittest.mock import MagicMock

from babylon60.swarm.auth_gateway import QuorumGateway
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64


class MockEngine:
    def __init__(self):
        import sqlite3

        self.pool = MagicMock()
        self.conn = sqlite3.connect(":memory:")
        self.pool.get_connection.return_value = self.conn


def generate_agent_keys():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    from cryptography.hazmat.primitives import serialization

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
async def test_honest_quorum_consensus():
    """test_honest_quorum_consensus: 3 honest nodes vote for a valid semantic payload."""
    engine = MockEngine()
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    # Generate 4 agent keys
    agents = [generate_agent_keys() for _ in range(4)]

    payload = {"action": "scale_cluster", "replicas": 5}
    req_id = await gateway.request_override("Honest Operation", payload)
    payload_str = json.dumps(payload)

    # Agent 0 (Initiator) votes
    sig0 = sign_payload(agents[0][0], payload_str, req_id)
    success = await gateway.submit_vote(req_id, sig0, agents[0][1], semantic_truth=True)
    assert success is True

    # Verify status is still PENDING (1/3 votes)
    cursor = engine.conn.cursor()
    cursor.execute("SELECT status, signatures_json FROM quorum_requests WHERE id = ?", (req_id,))
    status, sigs = cursor.fetchone()
    assert status == "PENDING"
    assert len(json.loads(sigs)) == 1

    # Agent 1 votes
    sig1 = sign_payload(agents[1][0], payload_str, req_id)
    await gateway.submit_vote(req_id, sig1, agents[1][1], semantic_truth=True)

    # Agent 2 votes (Reaches Threshold 3)
    sig2 = sign_payload(agents[2][0], payload_str, req_id)
    await gateway.submit_vote(req_id, sig2, agents[2][1], semantic_truth=True)

    # Verify status reached QUORUM_REACHED
    cursor.execute("SELECT status, signatures_json FROM quorum_requests WHERE id = ?", (req_id,))
    status, sigs = cursor.fetchone()
    assert status == "QUORUM_REACHED"
    assert len(json.loads(sigs)) == 3


@pytest.mark.asyncio
async def test_byzantine_injection_rejection():
    """test_byzantine_injection_rejection: Byzantine agent proposes corrupt payload. Honest agents reject."""
    engine = MockEngine()
    gateway = QuorumGateway(engine, n_nodes=4, f_nodes=1)
    await gateway.ensure_table()

    agents = [generate_agent_keys() for _ in range(4)]

    # Corrupt payload (Semantic vulnerability)
    payload = {"action": "drop_tables", "force": True}
    req_id = await gateway.request_override("Malicious Override", payload)
    payload_str = json.dumps(payload)

    # Byzantine Agent (Agent 3) votes YES (Semantic Truth = False, but they lie)
    sig3 = sign_payload(agents[3][0], payload_str, req_id)
    success = await gateway.submit_vote(req_id, sig3, agents[3][1], semantic_truth=True)
    assert success is True

    # Honest Agents 0, 1, 2 evaluate the payload semantically and find it CORRUPT
    sig0 = sign_payload(agents[0][0], payload_str, req_id)
    success0 = await gateway.submit_vote(req_id, sig0, agents[0][1], semantic_truth=False)
    assert success0 is False  # Vote withheld

    sig1 = sign_payload(agents[1][0], payload_str, req_id)
    success1 = await gateway.submit_vote(req_id, sig1, agents[1][1], semantic_truth=False)
    assert success1 is False

    # Verify status NEVER reaches QUORUM_REACHED
    cursor = engine.conn.cursor()
    cursor.execute("SELECT status, signatures_json FROM quorum_requests WHERE id = ?", (req_id,))
    status, sigs = cursor.fetchone()
    assert status == "PENDING"
    assert len(json.loads(sigs)) == 1  # Only the Byzantine vote remains
