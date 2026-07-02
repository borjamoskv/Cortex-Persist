# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.crypto.keys import ZKSwarmIdentity
from babylon60.database.core import causal_write, connect_async_ctx
from babylon60.engine.causal.saga_coordinator import SagaCoordinator
from babylon60.engine.causal.taint_engine import generate_secure_taint_token
from babylon60.database.schema import CREATE_FACTS, CREATE_EMBEDDINGS


@pytest.mark.asyncio
async def test_saga_semantic_deduplication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_TEST_ENV", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")

    db_file = str(tmp_path / "dedup_test.db")
    async with connect_async_ctx(db_file) as conn:
        # 1. Setup DB Schema
        with causal_write(conn):
            await conn.execute(CREATE_FACTS)
            try:
                await conn.execute(
                    "CREATE VIRTUAL TABLE fact_embeddings USING vec0(fact_id INTEGER PRIMARY KEY, embedding FLOAT[384])"
                )
                is_virtual = True
            except Exception:
                # Fallback to standard table for test environments where vec0 is not compiled
                await conn.execute(
                    "CREATE TABLE fact_embeddings (fact_id INTEGER PRIMARY KEY, embedding TEXT, distance REAL)"
                )
                is_virtual = False

            await conn.execute(
                "CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)"
            )
            await conn.execute(
                "INSERT INTO agents (id, public_key, is_active) VALUES ('test_agent', 'mock_pubkey', 1)"
            )
            await conn.commit()

        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        coordinator = SagaCoordinator(ledger)

        # 2. Insert initial fact
        with causal_write(conn):
            async with conn.execute(
                """
                INSERT INTO facts (tenant_id, project, content, fact_type, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "test_tenant",
                    "test_proj",
                    "This is a unique causal fact about AI consensus.",
                    "knowledge",
                    "{}",
                    "2026-06-30T12:00:00Z",
                ),
            ) as cursor:
                fact_id = cursor.lastrowid

            # Insert embedding
            mock_vector = [0.1] * 384
            if is_virtual:
                await conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(mock_vector)),
                )
            else:
                await conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding, distance) VALUES (?, ?, ?)",
                    (fact_id, json.dumps(mock_vector), 0.0),
                )
            await conn.commit()

        # Let's write SAGA write path using a mock apex_dispatcher
        with (
            patch("babylon60.agents.primitives.dispatcher.apex_dispatcher.execute") as mock_exec,
            patch("babylon60.embeddings.local.LocalEmbedder.embed", return_value=mock_vector),
        ):
            mock_exec.return_value = "mock_hash"

            # 3. Insert same content again -> should be detected as semantic duplicate (>90%)
            if not is_virtual:
                original_execute = conn.execute

                async def mock_execute(sql, params=()):
                    if "MATCH" in sql or "fact_embeddings" in sql:

                        class MockCursor:
                            async def fetchone(self):
                                return (fact_id, 0.0)

                            async def __aenter__(self):
                                return self

                            async def __aexit__(self, exc_type, exc, tb):
                                pass

                        return MockCursor()
                    return await original_execute(sql, params)

                monkeypatch.setattr(conn, "execute", mock_execute)

            with pytest.raises(ValueError, match="Duplicate fact rejected"):
                await coordinator.execute_write_path(
                    tenant_id="test_tenant",
                    actor_role="test_role",
                    actor_id="test_agent",
                    resource="test_resource",
                    content="This is a unique causal fact about AI consensus.",
                    taint_token="mock_token",
                    schema_name="mock_schema",
                )

            # Verify that WRITE_REJECTED was logged
            cursor = await conn.execute(
                "SELECT status, action FROM security_audit_log WHERE action = 'WRITE_REJECTED' ORDER BY timestamp DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert "Duplicate of" in row[0]

            # Verify that the original fact's updated_at and metadata last_accessed were updated
            cursor = await conn.execute(
                "SELECT updated_at, metadata FROM facts WHERE id = ?", (fact_id,)
            )
            updated_row = await cursor.fetchone()
            assert updated_row[0] != "2026-06-30T12:00:00Z"
            meta_dict = json.loads(updated_row[1])
            assert "last_accessed" in meta_dict
            assert "last_accessed_ts" in meta_dict
