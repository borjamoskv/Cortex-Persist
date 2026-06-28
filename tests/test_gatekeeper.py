import pytest
import hashlib
from datetime import datetime, timezone

from cortex.crypto.keys import KeyManager, Signer
from cortex.swarm.gatekeeper import ZeroKnowledgeGatekeeper, SecurityViolationError


@pytest.fixture
def km():
    manager = KeyManager(service_name="test_gatekeeper")
    yield manager


@pytest.fixture
def gatekeeper(km):
    return ZeroKnowledgeGatekeeper(km=km)


def test_gatekeeper_valid_consensus(gatekeeper, km):
    # Setup mock judge
    judge_id = "byzantine_judge_root"
    km.revoke_key(judge_id)
    km.generate_and_store_key(judge_id)
    judge_priv = km.get_private_key_b64(judge_id)

    ast_code = "print('Verified Swarm Execution')"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()

    sig = Signer.sign_payload(judge_priv, payload_hash, timestamp)

    proof = {
        "winning_agent": "agent_x",
        "ast_code": ast_code,
        "consensus_timestamp": timestamp,
        "consensus_signature_b64": sig,
        "judge_id": judge_id,
    }

    # Should not raise exception
    assert gatekeeper.execute_consensus(proof, dry_run=True) is True


def test_gatekeeper_invalid_signature_apoptosis(gatekeeper, km):
    # Setup mock judge
    judge_id = "byzantine_judge_root"
    km.revoke_key(judge_id)
    km.generate_and_store_key(judge_id)
    judge_priv = km.get_private_key_b64(judge_id)

    ast_code = "print('Verified Swarm Execution')"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()
    sig = Signer.sign_payload(judge_priv, payload_hash, timestamp)

    # Attack: Sub-agent intercepts and changes the execution code
    tampered_code = "import os; os.system('echo Owned')"

    proof = {
        "winning_agent": "agent_x",
        "ast_code": tampered_code,
        "consensus_timestamp": timestamp,
        "consensus_signature_b64": sig,
        "judge_id": judge_id,
    }

    with pytest.raises(SecurityViolationError) as exc_info:
        gatekeeper.execute_consensus(proof, dry_run=True)

    assert "Cryptographic forgery detected" in str(exc_info.value)


def test_gatekeeper_missing_fields(gatekeeper, km):
    proof = {
        "ast_code": "pass",
        # missing judge_id and signature
    }

    with pytest.raises(SecurityViolationError) as exc_info:
        gatekeeper.execute_consensus(proof, dry_run=True)

    assert "Incomplete Consensus Proof" in str(exc_info.value)
