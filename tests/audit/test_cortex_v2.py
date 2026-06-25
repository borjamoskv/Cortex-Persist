import pytest
import os
import json
import asyncio
from legacy_research.audit.ledger import EnterpriseAuditLedger
from legacy_research.crypto.identity import generate_event_identity
import cortex_core_rs

@pytest.mark.asyncio
async def test_full_cortex_v2_pipeline(tmp_path):
    log_file = str(tmp_path / "test_security_audit_log.jsonl")
    
    ledger = EnterpriseAuditLedger(log_path=log_file)
    ledger.batch_window_ms = 1 # fast batching for test
    ledger.max_batch_size = 2
    
    # 1. Test UUIDv7 Identity Generation
    ident1 = generate_event_identity()
    ident2 = generate_event_identity(trace_id=ident1.trace_id, parent_span_id=ident1.span_id)
    assert ident1.trace_id == ident2.trace_id
    assert ident2.lamport_time > ident1.lamport_time
    
    # 2. Test AST Canonicalization Hashing
    py_code_1 = "def x():\n    return 1"
    py_code_2 = "def x():\n  # A comment\n    return 1"
    hash1 = cortex_core_rs.hash_ast(py_code_1, "cpython-3.12")
    hash2 = cortex_core_rs.hash_ast(py_code_2, "cpython-3.12")
    assert hash1 == hash2 # Semantic equality despite comments/formatting
    
    # 3. Log actions into ledger to trigger batch Merkle tree
    await ledger.log_action(
        tenant_id="tenant_1",
        actor_role="admin",
        actor_id="user_1",
        action="CREATE_NODE",
        resource="graph_db",
        state_diff=json.dumps([{"op": "add", "path": "/node_1", "value": "test"}])
    )
    
    await ledger.log_action(
        tenant_id="tenant_1",
        actor_role="admin",
        actor_id="user_1",
        action="UPDATE_NODE",
        resource="graph_db",
        state_diff=json.dumps([{"op": "replace", "path": "/node_1", "value": "test_updated", "old_value": "test"}])
    )
    
    # Give time for the batch worker to trigger and flush
    await asyncio.sleep(0.1)
    
    # Verify JSONL log contains the batch root
    assert os.path.exists(log_file)
    with open(log_file) as f:
        lines = f.readlines()
        
    assert len(lines) == 3 # 2 events + 1 BATCH_ROOT
    batch_root_event = json.loads(lines[2])
    assert batch_root_event["type"] == "BATCH_ROOT"
    assert "signature" in batch_root_event
    
    # Verify we can replay
    from cortex.engine.replay_verifier import ReplayVerifier
    verifier = ReplayVerifier(log_path=log_file)
    exec_events = [e for e in verifier.events if e.get("type") != "BATCH_ROOT"]
    assert len(exec_events) == 2
