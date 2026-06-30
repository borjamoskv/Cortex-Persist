# [C5-REAL] Exergy-Maximized
"""
E2E Test for the SAGA Write-Path Orchestrator.
Validates the Victoria Visible 7 Días requirement.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.crypto.keys import ZKSwarmIdentity
from babylon60.database.core import causal_write, connect_async_ctx
from babylon60.engine.causal.saga_coordinator import SagaCoordinator
from babylon60.engine.causal.taint_engine import generate_secure_taint_token


@pytest.fixture
def clean_payload() -> str:
    return json.dumps({"action": "crystalline_state_mutation", "data": "clean content"})


@pytest.mark.asyncio
async def test_saga_write_path_success(tmp_path: Path, clean_payload: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_TEST_ENV", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "0")
    
    db_file = str(tmp_path / "saga_test.db")
    keypair = ZKSwarmIdentity.generate_keypair()
    
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            await conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
            await conn.execute("INSERT INTO agents (id, public_key, is_active) VALUES ('test_agent', ?, 1)", (keypair.public_key_b64,))
            await conn.commit()
            
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        coordinator = SagaCoordinator(ledger)
        
        token = generate_secure_taint_token(
            agent_id="test_agent",
            session_id="test_session",
            content=clean_payload,
            private_key_b64=keypair.private_key_b64,
            curve="ed25519"
        )
        
        # We must patch apex_dispatcher.execute so it doesn't run real git commands during test
        with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_exec:
            mock_exec.return_value = "mock_hash"
            
            audit_id = await coordinator.execute_write_path(
                tenant_id="test_tenant",
                actor_role="test_role",
                actor_id="test_agent",
                resource="test_resource",
                content=clean_payload,
                taint_token=token,
                schema_name="mock_schema"
            )
            
            assert audit_id is not None
            
            # Verify Ledger Entry SAGA-5
            cursor = await conn.execute(
                "SELECT status, action FROM security_audit_log WHERE audit_id = ?", 
                (audit_id,)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "SUCCESS"
            assert row[1] == "WRITE_COMMITTED"
            
            # Verify OP_FREEZE_MEM and OP_GIT_SENTINEL were invoked (SAGA-7)
            assert mock_exec.call_count == 2
            mock_exec.assert_any_call("OP_GIT_SENTINEL", commit_msg="CORTEX-TAINT: Causal state commit for [test_agent]", force=False)


@pytest.mark.asyncio
async def test_saga_write_path_invalid_taint(tmp_path: Path, clean_payload: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_TEST_ENV", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "0")
    
    db_file = str(tmp_path / "saga_test_fail.db")
    keypair = ZKSwarmIdentity.generate_keypair()
    
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            await conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
            await conn.execute("INSERT INTO agents (id, public_key, is_active) VALUES ('test_agent', ?, 1)", (keypair.public_key_b64,))
            await conn.commit()
            
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        coordinator = SagaCoordinator(ledger)
        
        # Use an invalid token to trigger SAGA abort
        invalid_token = "moskv-taint:ed25519:test_agent:session:timestamp:nonce:invalidsig"
        
        with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_exec:
            with pytest.raises(ValueError, match="SAGA Aborted"):
                await coordinator.execute_write_path(
                    tenant_id="test_tenant",
                    actor_role="test_role",
                    actor_id="test_agent",
                    resource="test_resource",
                    content=clean_payload,
                    taint_token=invalid_token,
                    schema_name="mock_schema"
                )
            
            # OP_GIT_SENTINEL should NOT be called
            mock_exec.assert_not_called()
            
            # Verify Rejection Ledger Entry
            cursor = await conn.execute(
                "SELECT status, action FROM security_audit_log WHERE status LIKE '%Valid cryptographically signed CORTEX-TAINT token is required%'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[1] == "WRITE_REJECTED"


@pytest.mark.asyncio
async def test_saga_write_path_with_encryption(tmp_path: Path, clean_payload: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_TEST_ENV", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "0")
    # Provide a dummy 32-byte master key (hex) to activate encryption
    monkeypatch.setenv("CORTEX_ENCRYPTION_KEY", "0" * 64)
    
    # We must reset the encrypter so it picks up the new master key
    from babylon60.crypto.aes import reset_default_encrypter
    reset_default_encrypter()
    
    db_file = str(tmp_path / "saga_test_encrypt.db")
    keypair = ZKSwarmIdentity.generate_keypair()
    
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            await conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
            await conn.execute("INSERT INTO agents (id, public_key, is_active) VALUES ('test_agent', ?, 1)", (keypair.public_key_b64,))
            await conn.commit()
            
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        coordinator = SagaCoordinator(ledger)
        
        token = generate_secure_taint_token(
            agent_id="test_agent",
            session_id="test_session",
            content=clean_payload,
            private_key_b64=keypair.private_key_b64,
            curve="ed25519"
        )
        
        with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_exec:
            mock_exec.return_value = "mock_hash"
            
            # Request encryption via metadata
            metadata = {"encrypt": True}
            
            audit_id = await coordinator.execute_write_path(
                tenant_id="test_tenant",
                actor_role="test_role",
                actor_id="test_agent",
                resource="test_resource",
                content=clean_payload,
                taint_token=token,
                schema_name="mock_schema",
                metadata=metadata
            )
            
            assert audit_id is not None
            # Check that content was actually encrypted in the metadata trace before passing to secure_state_commit
            assert metadata.get("cortex_encrypted") is True
            
            # Extract the actual state frozen in OP_FREEZE_MEM
            # mock_exec.call_args_list[0] is OP_FREEZE_MEM
            freeze_call = mock_exec.call_args_list[0]
            frozen_state = freeze_call.kwargs.get("state")
            assert frozen_state is not None
            
            # The content sent to freeze should now be an encrypted string starting with AESGCM prefix
            frozen_content = frozen_state["content"]
            assert frozen_content.startswith("v6_aesgcm:")
            assert frozen_content != clean_payload


@pytest.mark.asyncio
async def test_saga_write_path_bft_quorum(tmp_path: Path, clean_payload: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_TEST_ENV", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "0")
    
    db_file = str(tmp_path / "saga_test_bft.db")
    
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    import base64
    
    # Generate N=4 peers
    peers = {
        f"peer_{i}": ZKSwarmIdentity.generate_keypair() for i in range(4)
    }
    
    known_peers = {}
    priv_keys = {}
    for pid, kp in peers.items():
        pub_bytes = base64.b64decode(kp.public_key_b64)
        known_peers[pid] = serialization.load_ssh_public_key(pub_bytes)
        
        priv_bytes = base64.b64decode(kp.private_key_b64)
        priv_keys[pid] = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    
    # F = (4-1)//3 = 1. Required Quorum = 2f+1 = 3.
    
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            await conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
            await conn.execute("INSERT INTO agents (id, public_key, is_active) VALUES ('test_agent', ?, 1)", (peers["peer_0"].public_key_b64,))
            await conn.commit()
            
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        coordinator = SagaCoordinator(ledger)
        
        # Primary taint token from peer_0
        token1 = generate_secure_taint_token(
            agent_id="test_agent",
            session_id="test_session",
            content=clean_payload,
            private_key_b64=peers["peer_0"].private_key_b64,
            curve="ed25519"
        )
        
        # 1) Generate signatures from 2 peers (less than quorum of 3)
        bft_sigs_failed = {
            "peer_0": priv_keys["peer_0"].sign(clean_payload.encode('utf-8')),
            "peer_1": priv_keys["peer_1"].sign(clean_payload.encode('utf-8'))
        }
        
        metadata_failed = {
            "bft_signatures": bft_sigs_failed,
            "bft_known_peers": known_peers
        }
        
        # Should fail with ValueError containing BFTQuorumError
        with pytest.raises(ValueError, match="SAGA Aborted: Ouroboros Quorum NOT met"):
            await coordinator.execute_write_path(
                tenant_id="test_tenant",
                actor_role="test_role",
                actor_id="test_agent",
                resource="test_resource",
                content=clean_payload,
                taint_token=token1,
                schema_name="mock_schema",
                metadata=metadata_failed
            )
            
        token2 = generate_secure_taint_token(
            agent_id="test_agent",
            session_id="test_session",
            content=clean_payload,
            private_key_b64=peers["peer_0"].private_key_b64,
            curve="ed25519"
        )

        # 2) Generate signatures from 3 peers (meets quorum of 3)
        bft_sigs_success = {
            "peer_0": priv_keys["peer_0"].sign(clean_payload.encode('utf-8')),
            "peer_1": priv_keys["peer_1"].sign(clean_payload.encode('utf-8')),
            "peer_2": priv_keys["peer_2"].sign(clean_payload.encode('utf-8'))
        }
        
        metadata_success = {
            "bft_signatures": bft_sigs_success,
            "bft_known_peers": known_peers
        }
        
        with patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_exec:
            mock_exec.return_value = "mock_hash"
            
            audit_id = await coordinator.execute_write_path(
                tenant_id="test_tenant",
                actor_role="test_role",
                actor_id="test_agent",
                resource="test_resource",
                content=clean_payload,
                taint_token=token2,
                schema_name="mock_schema",
                metadata=metadata_success
            )
            
            assert audit_id is not None
            assert mock_exec.called
