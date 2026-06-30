import asyncio
import json
import uuid
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.database.core import causal_write, connect_async_ctx
from babylon60.engine.causal.saga_coordinator import SagaCoordinator
from babylon60.engine.causal.taint_engine import generate_secure_taint_token
from babylon60.crypto.keys import ZKSwarmIdentity


async def worker_task(worker_id: int, coordinator: SagaCoordinator, db_file: str, known_peers: dict, priv_keys: dict, worker_priv_key_b64: str):
    # Unique content for each worker
    content = json.dumps({
        "action": f"stress_mutation_{worker_id}",
        "data": f"content from worker {worker_id}",
        "nonce": uuid.uuid4().hex
    })
    
    # Generate token
    token = generate_secure_taint_token(
        agent_id=f"agent_{worker_id}",
        session_id="stress_session",
        content=content,
        private_key_b64=worker_priv_key_b64,
        curve="ed25519"
    )
    
    # BFT Sigs
    bft_sigs = {
        "peer_0": priv_keys["peer_0"].sign(content.encode('utf-8')),
        "peer_1": priv_keys["peer_1"].sign(content.encode('utf-8')),
        "peer_2": priv_keys["peer_2"].sign(content.encode('utf-8'))
    }
    
    metadata = {
        "bft_signatures": bft_sigs,
        "bft_known_peers": known_peers
    }
    
    # We expect this to succeed without locking errors
    audit_id = await coordinator.execute_write_path(
        tenant_id="stress_tenant",
        actor_role="stress_worker",
        actor_id=f"agent_{worker_id}",
        resource=f"resource_{worker_id}",
        content=content,
        taint_token=token,
        schema_name="mock_schema",
        metadata=metadata
    )
    
    return audit_id


@pytest.mark.asyncio
async def test_saga_coordinator_stress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    STRESS TEST: Ensures SQLite WAL with busy_timeout=5000ms can handle 
    massive concurrent BFT-validated writes without thermodynamic deadlocks.
    """
    from unittest.mock import patch
    import base64
    
    monkeypatch.setenv("CORTEX_TEST_ENV", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "0")
    
    db_file = str(tmp_path / "saga_stress.db")
    
    # N=4 peers
    peers = {f"peer_{i}": ZKSwarmIdentity.generate_keypair() for i in range(4)}
    
    known_peers = {}
    priv_keys = {}
    for pid, kp in peers.items():
        pub_bytes = base64.b64decode(kp.public_key_b64)
        known_peers[pid] = serialization.load_ssh_public_key(pub_bytes)
        priv_bytes = base64.b64decode(kp.private_key_b64)
        priv_keys[pid] = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    
    # Setup DB
    worker_keys = {}
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            await conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
            # Insert all workers into the agents table so Taint Engine can verify them
            NUM_WORKERS = 50
            for i in range(NUM_WORKERS):
                kp = ZKSwarmIdentity.generate_keypair()
                worker_keys[i] = kp.private_key_b64
                await conn.execute(
                    "INSERT INTO agents (id, public_key, is_active) VALUES (?, ?, 1)",
                    (f"agent_{i}", kp.public_key_b64)
                )
            await conn.commit()
            
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        coordinator = SagaCoordinator(ledger)
        
        with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_exec:
            mock_exec.return_value = "mock_hash_stress"
            
            tasks = [
                worker_task(i, coordinator, db_file, known_peers, priv_keys, worker_keys[i]) 
                for i in range(NUM_WORKERS)
            ]
            
            # Execute them all concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            successes = [r for r in results if isinstance(r, str)]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # All 50 should succeed
            assert len(successes) == NUM_WORKERS, f"Stress test failed with exceptions: {exceptions}"
            assert len(exceptions) == 0
