import base64
import hashlib
import json
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

try:
    from fastapi.testclient import TestClient
    from cortex.swarm.inference_proxy import app
    from cortex.consensus.pki import trust_matrix

    client = TestClient(app)
except ImportError:
    pytest.skip("FastAPI not installed, skipping proxy tests", allow_module_level=True)


@pytest.fixture(autouse=True)
def setup_mock_env(monkeypatch):
    monkeypatch.setenv("CORTEX_TESTING", "1")


@pytest.fixture
def registered_agent():
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    agent_id = "test_agent_proxy"

    # Register directly in TrustMatrix for test purposes
    trust_matrix._peers[agent_id] = pub_key

    yield agent_id, priv_key

    # Teardown
    if agent_id in trust_matrix._peers:
        del trust_matrix._peers[agent_id]


def test_inference_proxy_success(registered_agent):
    agent_id, priv_key = registered_agent
    prompt = "Explain quantum entropy."

    # Sign the prompt
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).digest()
    sig_b64 = base64.b64encode(priv_key.sign(prompt_hash)).decode("ascii")

    payload = {"agent_id": agent_id, "prompt": prompt, "signature_b64": sig_b64}

    response = client.post("/v1/inference", json=payload)

    assert response.status_code == 200
    assert "MOCK_RESPONSE_FOR_test_agent_proxy" in response.json()["response"]


def test_inference_proxy_unregistered_agent():
    # Agent not in trust matrix
    agent_id = "ghost_agent"
    priv_key = ed25519.Ed25519PrivateKey.generate()
    prompt = "Hello"
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).digest()
    sig_b64 = base64.b64encode(priv_key.sign(prompt_hash)).decode("ascii")

    payload = {"agent_id": agent_id, "prompt": prompt, "signature_b64": sig_b64}

    response = client.post("/v1/inference", json=payload)
    assert response.status_code == 403
    assert "Not Found or Revoked" in response.text


def test_inference_proxy_invalid_signature(registered_agent):
    agent_id, priv_key = registered_agent
    prompt = "Hello"

    # Sign a DIFFERENT prompt
    wrong_hash = hashlib.sha256(b"Goodbye").digest()
    sig_b64 = base64.b64encode(priv_key.sign(wrong_hash)).decode("ascii")

    payload = {"agent_id": agent_id, "prompt": prompt, "signature_b64": sig_b64}

    response = client.post("/v1/inference", json=payload)
    assert response.status_code == 403
    assert "Invalid Signature" in response.text
