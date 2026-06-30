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
