import pytest
import hashlib
from datetime import datetime, timezone

from cortex.crypto.keys import KeyManager, Signer, Verifier
from cortex.swarm.byzantine_judge import ByzantineJudge
from cortex.engine.uncategorized.sandbox_jit import SandboxJIT

# To mock SandboxJIT successfully since we don't need real execution logic here
class MockSandboxJIT:
    def execute(self, code, context):
        if "VIOLATION" in code:
            from cortex.engine.uncategorized.sandbox_jit import JITSandboxViolation
            raise JITSandboxViolation("Mock violation")
        return context

@pytest.fixture
def judge(monkeypatch, km):
    monkeypatch.setattr("cortex.swarm.byzantine_judge.SandboxJIT", MockSandboxJIT)
    # Give the judge a clean DB context for exergy
    j = ByzantineJudge(km=km)
    yield j

@pytest.fixture
def km():
    manager = KeyManager(service_name="test_swarm_judge")
    yield manager

def test_byzantine_judge_valid_consensus(judge, km):
    # Setup Agents
    agent_id = "agent_valid_1"
    km.revoke_key(agent_id)
    km.generate_and_store_key(agent_id)
    priv = km.get_private_key_b64(agent_id)
    
    ast_code = "def valid_ast(): pass"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()
    
    sig = Signer.sign_payload(priv, payload_hash, timestamp)
    
    proposals = [
        {
            "agent_id": agent_id,
            "ast_code": ast_code,
            "signature_b64": sig,
            "timestamp": timestamp
        }
    ]
    
    result = judge.evaluate_proposals({}, proposals)
    assert result is not None
    assert result["winning_agent"] == agent_id
    assert result["ast_code"] == ast_code
    
    # Check that Judge signed the consensus proof correctly
    judge_pub = km.get_public_key_b64(result["judge_id"])
    assert judge_pub is not None
    
    c_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()
    assert Verifier.verify_signature(
        judge_pub, 
        c_hash, 
        result["consensus_timestamp"], 
        result["consensus_signature_b64"]
    ) is True

def test_byzantine_judge_spoofed_signature(judge, km):
    # Setup valid agent
    agent_id = "agent_valid_2"
    km.revoke_key(agent_id)
    km.generate_and_store_key(agent_id)
    priv = km.get_private_key_b64(agent_id)
    
    # Valid code
    ast_code = "def valid_ast(): pass"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()
    sig = Signer.sign_payload(priv, payload_hash, timestamp)
    
    # Attacker mutates the code but uses the original signature
    tampered_ast = "def valid_ast(): import os; os.system('rm -rf /')"
    
    proposals = [
        {
            "agent_id": agent_id,
            "ast_code": tampered_ast,  # spoofed
            "signature_b64": sig,
            "timestamp": timestamp
        }
    ]
    
    result = judge.evaluate_proposals({}, proposals)
    # The signature will be rejected because payload_hash won't match
    assert result is None
    
    # The agent should have been slashed
    wallet = judge.bank.register_agent(agent_id)
    from cortex.swarm.exergy import ExergyBank
    assert wallet.failed_commits > 0 or wallet.balance < ExergyBank.INITIAL_EXERGY

def test_byzantine_judge_jit_enrollment(judge, km):
    # Agent not pre-registered
    agent_id = "agent_unregistered_1"
    km.revoke_key(agent_id)
    
    ast_code = "def valid_ast(): pass"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Attacker tries to submit random signature for unregistered agent
    proposals = [
        {
            "agent_id": agent_id,
            "ast_code": ast_code,
            "signature_b64": "random_fake_signature_that_fails_validation",
            "timestamp": timestamp
        }
    ]
    
    result = judge.evaluate_proposals({}, proposals)
    assert result is None
