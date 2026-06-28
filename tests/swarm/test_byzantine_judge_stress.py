import asyncio
import hashlib
import pytest
import shutil
from datetime import datetime, timezone
from pathlib import Path

from cortex.crypto.keys import KeyManager, Signer, Verifier
from cortex.swarm.byzantine_judge import ByzantineJudge
from cortex.swarm.exergy import ExergyBank
from cortex.engine.core.sandbox_jit import JITSandboxViolation, SandboxJIT

# We will test both real execution and simulated host crashes.
# To simulate a host crash, we can monkeypatch SandboxJIT.execute to raise a base Exception.


@pytest.fixture
def clean_km(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("cortex.crypto.keys.keyring", None)
    # Use an isolated KeyManager for the stress test
    manager = KeyManager(service_name="stress_swarm_judge")
    yield manager
    # Clean up keys directory if necessary, but keep it for test assertions if needed
    if manager.db_path.exists():
        manager.db_path.unlink()


@pytest.mark.asyncio
async def test_byzantine_judge_concurrent_stress(clean_km):
    """
    Sovereign Byzantine BFT Stress Test.
    Concurrently bombards ByzantineJudge with:
      - Valid proposals (rewarded).
      - Malformed proposals (slashed/ignored).
      - Spoofed proposals (slashed).
      - Sandbox violations (slashed).
      - AST runtime execution errors (slashed).
    """
    judge = ByzantineJudge(km=clean_km)

    # 1. Setup 50 agents
    num_agents = 50
    agent_ids = [f"agent_stress_{i}" for i in range(num_agents)]

    # Generate keys for all agents
    for aid in agent_ids:
        clean_km.revoke_key(aid)
        clean_km.generate_and_store_key(aid)

    # Define proposal generator helper
    def make_proposal(agent_id, ast_code, tamper_sig=False, invalid_sig=False):
        priv = clean_km.get_private_key_b64(agent_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()

        if invalid_sig:
            sig = "invalid_signature_hex"
        else:
            sig = Signer.sign_payload(priv, payload_hash, timestamp)

        if tamper_sig:
            # Code is tampered but signature remains the same (mismatched payload hash)
            ast_code = ast_code + "\n# tampered"

        return {
            "agent_id": agent_id,
            "ast_code": ast_code,
            "signature_b64": sig,
            "timestamp": timestamp,
        }

    # Prepare various types of proposals
    proposals = []

    # Category A: Valid Proposals (10 agents)
    for i in range(10):
        aid = agent_ids[i]
        code = f"x = {i}\ny = x + 1"
        proposals.append(make_proposal(aid, code))

    # Category B: Malformed Proposals (10 agents) - missing cryptographic fields
    for i in range(10, 20):
        aid = agent_ids[i]
        # Lacks signature
        proposals.append(
            {
                "agent_id": aid,
                "ast_code": "x = 1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Category C: Spoofed/Tampered Proposals (10 agents)
    for i in range(20, 30):
        aid = agent_ids[i]
        code = "x = 100"
        proposals.append(make_proposal(aid, code, tamper_sig=True))

    # Category D: Sandbox Violations (10 agents)
    for i in range(30, 40):
        aid = agent_ids[i]
        # Import os is forbidden
        code = "import os\nos.system('echo violation')"
        proposals.append(make_proposal(aid, code))

    # Category E: AST Runtime Execution Errors (10 agents)
    for i in range(40, 50):
        aid = agent_ids[i]
        # Divide by zero error
        code = "x = 1 / 0"
        proposals.append(make_proposal(aid, code))

    # Run evaluations concurrently (simulating multiple proposal bursts)
    # Since ByzantineJudge.evaluate_proposals is synchronous, we run it in executor threads
    loop = asyncio.get_running_loop()

    def run_eval():
        # Evaluate all 50 proposals together
        return judge.evaluate_proposals({"initial_state_val": 42}, proposals)

    # Dispatch 20 concurrent bursts of proposal evaluations
    tasks = [loop.run_in_executor(None, run_eval) for _ in range(20)]
    results = await asyncio.gather(*tasks)

    # 2. Assert BFT Slashing and Rewards
    for result in results:
        assert result is not None
        # Winner must be from the valid proposals group (agent_stress_0 to agent_stress_9)
        assert result["winning_agent"] in agent_ids[0:10]

    # Let's inspect Exergy balances of all agents
    bank = judge.bank

    # Category A (Valid) should have successful_commits > 0, balance > 1000
    for i in range(10):
        wallet = bank.wallets[agent_ids[i]]
        assert wallet.successful_commits > 0
        assert wallet.failed_commits == 0
        assert wallet.balance > ExergyBank.INITIAL_EXERGY

    # Category B (Malformed) should have failed_commits > 0, balance < 1000
    for i in range(10, 20):
        wallet = bank.wallets[agent_ids[i]]
        assert wallet.failed_commits > 0
        assert wallet.balance < ExergyBank.INITIAL_EXERGY

    # Category C (Spoofed) should have failed_commits > 0, balance < 1000
    for i in range(20, 30):
        wallet = bank.wallets[agent_ids[i]]
        assert wallet.failed_commits > 0
        assert wallet.balance < ExergyBank.INITIAL_EXERGY

    # Category D (Sandbox Violation) should have failed_commits > 0, balance < 1000
    for i in range(30, 40):
        wallet = bank.wallets[agent_ids[i]]
        assert wallet.failed_commits > 0
        assert wallet.balance < ExergyBank.INITIAL_EXERGY

    # Category E (AST Runtime Error) should have failed_commits > 0, balance < 1000
    for i in range(40, 50):
        wallet = bank.wallets[agent_ids[i]]
        assert wallet.failed_commits > 0
        assert wallet.balance < ExergyBank.INITIAL_EXERGY


@pytest.mark.asyncio
async def test_byzantine_judge_host_crash_isolation(monkeypatch, clean_km):
    """
    Verify that simulated host-level exceptions (e.g. hardware faults, memory exhaustion, unhandled host errors)
    do NOT result in agent slashing. It must halt the consensus and raise a RuntimeError.
    """
    judge = ByzantineJudge(km=clean_km)

    agent_id = "agent_host_test"
    clean_km.revoke_key(agent_id)
    clean_km.generate_and_store_key(agent_id)

    ast_code = "x = 1"
    priv = clean_km.get_private_key_b64(agent_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha256(ast_code.encode("utf-8")).hexdigest()
    sig = Signer.sign_payload(priv, payload_hash, timestamp)

    proposal = {
        "agent_id": agent_id,
        "ast_code": ast_code,
        "signature_b64": sig,
        "timestamp": timestamp,
    }

    # Mock SandboxJIT to throw a generic Exception (simulating host system crash)
    def mock_host_crash(*args, **kwargs):
        raise OSError("Host System Memory Exhaustion or DB Lock deadlock")

    monkeypatch.setattr(judge.sandbox, "execute", mock_host_crash)

    # Evaluate proposal - should halt and raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        judge.evaluate_proposals({}, [proposal])

    assert "Host execution degraded" in str(exc_info.value)

    # Ensure agent was NOT slashed (no failed commits added, balance remains Initial or only staked amount returned)
    wallet = judge.bank.wallets[agent_id]
    assert wallet.failed_commits == 0
    # The stake should be returned or not slashed. Since stake deducts 50 and reward adds it back,
    # let's verify that the wallet was not slashed (wallet.failed_commits remains 0).
    assert wallet.failed_commits == 0
