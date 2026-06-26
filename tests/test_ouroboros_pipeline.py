import pytest
import hashlib
from datetime import datetime, timezone

from cortex.crypto.keys import KeyManager, Signer
from cortex.swarm.byzantine_judge import ByzantineJudge
from cortex.swarm.gatekeeper import ZeroKnowledgeGatekeeper

# Mocking SandboxJIT again for pipeline testing
class MockSandboxJIT:
    def execute(self, code, context):
        if "VIOLATION" in code:
            from cortex.engine.uncategorized.sandbox_jit import JITSandboxViolation
            raise JITSandboxViolation("Pipeline violation")
        return context

@pytest.fixture
def km():
    manager = KeyManager(service_name="ouroboros_pipeline")
    yield manager

@pytest.fixture
def judge(monkeypatch, km):
    monkeypatch.setattr("cortex.swarm.byzantine_judge.SandboxJIT", MockSandboxJIT)
    return ByzantineJudge(km=km)

@pytest.fixture
def gatekeeper(km):
    return ZeroKnowledgeGatekeeper(km=km)

def test_ouroboros_transcend_pipeline(judge, gatekeeper, km):
    """
    Test the full Auto-Evolution pipeline for Ouroboros.
    1. Agent proposes AST mutation.
    2. Byzantine Judge validates and creates ConsensusProof.
    3. Gatekeeper validates ConsensusProof and "executes".
    """
    agent_id = "ouroboros_agent_root"
    km.revoke_key(agent_id)
    km.generate_and_store_key(agent_id)
    agent_priv = km.get_private_key_b64(agent_id)
    
    km.revoke_key(judge.judge_id)
    km.generate_and_store_key(judge.judge_id)
    
    ast_code = "def autopoiesis(): return 'evolution completed'"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()
    
    sig = Signer.sign_payload(agent_priv, payload_hash, timestamp)
    
    # 1. Propose
    proposals = [
        {
            "agent_id": agent_id,
            "ast_code": ast_code,
            "signature_b64": sig,
            "timestamp": timestamp
        }
    ]
    
    # 2. Consensus
    proof = judge.evaluate_proposals({}, proposals)
    assert proof is not None
    assert proof["winning_agent"] == agent_id
    assert proof["judge_id"] == judge.judge_id
    
    # 3. Execution via Gatekeeper
    # This acts as the final CI step simulation
    execution_result = gatekeeper.execute_consensus(proof, dry_run=True)
    assert execution_result is True
