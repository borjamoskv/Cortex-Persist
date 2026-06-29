# [C5-REAL] Exergy-Maximized
# Test suite for cortex/engine/causal/taint_engine.py

from __future__ import annotations

import asyncio
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

from cortex.crypto.keys import ZKSwarmIdentity
from cortex.database.core import connect, connect_async_ctx, causal_write
from cortex.engine.causal.taint_engine import (
    TaintValidationError,
    canonicalize_content,
    _fast_sha3,
    generate_secure_taint_token,
    parse_utc_timestamp,
    verify_taint_token,
    enforce_taint_check,
    MHCAntigenRouter,
    secure_state_commit,
)


def test_canonicalize_content() -> None:
    # Test raw string normalization
    assert canonicalize_content("  test content  \n  next line  ") == b"test content\nnext line"
    
    # Test JSON deterministic normalization
    json_str = '{"b": 2, "a": 1}'
    assert canonicalize_content(json_str) == b'{"a":1,"b":2}'
    
    # Test non-JSON string normalization fallback
    assert canonicalize_content("not-json") == b"not-json"
    
    # Test memoryview content
    mv = memoryview(b"memoryview content")
    assert canonicalize_content(mv) == b"memoryview content"


def test_fast_sha3() -> None:
    content = b"crystallized state"
    h1 = _fast_sha3(content)
    assert len(h1) == 64
    assert h1 == _fast_sha3(memoryview(content))


def test_parse_utc_timestamp() -> None:
    ts = "2026-06-29T12:00:00Z"
    dt = parse_utc_timestamp(ts)
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 12

    ts_no_z = "2026-06-29T12:00:00"
    dt_no_z = parse_utc_timestamp(ts_no_z)
    assert dt_no_z.tzinfo == timezone.utc


def test_generate_secure_taint_token_ed25519() -> None:
    keypair = ZKSwarmIdentity.generate_keypair()
    content = "agent state payload"
    
    token = generate_secure_taint_token(
        agent_id="agent_1",
        session_id="session_1",
        content=content,
        private_key_b64=keypair.private_key_b64,
        curve="ed25519",
    )
    
    assert token.startswith("taint:")
    parts = token.split(":")
    assert len(parts) >= 6
    assert parts[0] == "taint"
    assert parts[1] == "agent_1"
    assert parts[2] == "session_1"


def test_generate_secure_taint_token_secp256k1() -> None:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    import base64

    priv_key = ec.generate_private_key(ec.SECP256K1())
    priv_bytes = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_b64 = base64.b64encode(priv_bytes).decode("utf-8")

    content = "agent state payload"
    token = generate_secure_taint_token(
        agent_id="agent_1",
        session_id="session_1",
        content=content,
        private_key_b64=priv_b64,
        curve="secp256k1",
    )
    
    assert token.startswith("taint:secp256k1:")
    parts = token.split(":")
    assert len(parts) >= 7
    assert parts[0] == "taint"
    assert parts[1] == "secp256k1"
    assert parts[2] == "agent_1"


@pytest.fixture
def sqlite_conn() -> sqlite3.Connection:
    # Use CORTEX factory connection allocator to pass C5-REAL security constraints
    conn = connect(":memory:")
    with causal_write(conn):
        conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
        conn.commit()
    return conn


@pytest.mark.asyncio
async def test_verify_taint_token_sync(sqlite_conn: sqlite3.Connection) -> None:
    keypair = ZKSwarmIdentity.generate_keypair()
    content = "agent state payload"
    
    with causal_write(sqlite_conn):
        sqlite_conn.execute(
            "INSERT INTO agents (id, public_key, is_active) VALUES ('agent_1', ?, 1)",
            (keypair.public_key_b64,),
        )
        sqlite_conn.commit()

    token = generate_secure_taint_token(
        agent_id="agent_1",
        session_id="session_1",
        content=content,
        private_key_b64=keypair.private_key_b64,
        curve="ed25519",
    )

    # Validate valid token
    assert await verify_taint_token(sqlite_conn, token, content) is True

    # Validate incorrect content
    assert await verify_taint_token(sqlite_conn, token, "different content") is False

    # Validate malformed token
    assert await verify_taint_token(sqlite_conn, "invalid_token", content) is False
    assert await verify_taint_token(sqlite_conn, "taint:short", content) is False


@pytest.mark.asyncio
async def test_verify_taint_token_async(tmp_path: Path) -> None:
    keypair = ZKSwarmIdentity.generate_keypair()
    content = "agent state payload"
    db_file = str(tmp_path / "taint_test.db")

    # Use connect_async_ctx context manager with a real file to satisfy CortexConnection factory requirements
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            async with conn.cursor() as cursor:
                await cursor.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)")
                await cursor.execute(
                    "INSERT INTO agents (id, public_key, is_active) VALUES ('agent_1', ?, 1)",
                    (keypair.public_key_b64,),
                )
                await conn.commit()

        token = generate_secure_taint_token(
            agent_id="agent_1",
            session_id="session_1",
            content=content,
            private_key_b64=keypair.private_key_b64,
            curve="ed25519",
        )

        assert await verify_taint_token(conn, token, content) is True


@pytest.mark.asyncio
async def test_verify_taint_token_expired(sqlite_conn: sqlite3.Connection) -> None:
    keypair = ZKSwarmIdentity.generate_keypair()
    content = "agent state payload"

    with causal_write(sqlite_conn):
        sqlite_conn.execute(
            "INSERT INTO agents (id, public_key, is_active) VALUES ('agent_1', ?, 1)",
            (keypair.public_key_b64,),
        )
        sqlite_conn.commit()

    # Create a token manually but change timestamp to be > 300 seconds ago
    timestamp = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
    nonce = "nonce123"
    
    canonical_content = canonicalize_content(content)
    content_hash = _fast_sha3(canonical_content)
    canonical_payload = f"agent_id=agent_1&session_id=session_1&timestamp={timestamp}&nonce={nonce}&content_hash={content_hash}"
    
    from cortex.crypto.keys import Signer
    signature = Signer.sign_raw_content(keypair.private_key_b64, canonical_payload)
    token = f"taint:agent_1:session_1:{timestamp}:{nonce}:{signature}"

    assert await verify_taint_token(sqlite_conn, token, content) is False


@pytest.mark.asyncio
async def test_verify_taint_token_replay_attack(sqlite_conn: sqlite3.Connection) -> None:
    keypair = ZKSwarmIdentity.generate_keypair()
    content = "agent state payload"

    with causal_write(sqlite_conn):
        sqlite_conn.execute(
            "INSERT INTO agents (id, public_key, is_active) VALUES ('agent_1', ?, 1)",
            (keypair.public_key_b64,),
        )
        sqlite_conn.commit()

    token = generate_secure_taint_token(
        agent_id="agent_1",
        session_id="session_1",
        content=content,
        private_key_b64=keypair.private_key_b64,
        nonce="unique_nonce_1",
        curve="ed25519",
    )

    # First verification should pass and register the nonce
    assert await verify_taint_token(sqlite_conn, token, content) is True

    # Second verification with same nonce/token should detect replay attack and fail
    assert await verify_taint_token(sqlite_conn, token, content) is False


@pytest.mark.asyncio
async def test_enforce_taint_check_bypass(sqlite_conn: sqlite3.Connection) -> None:
    os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
    try:
        # Should bypass verify_taint_token check and return None
        await enforce_taint_check(sqlite_conn, None, "any content")
    finally:
        del os.environ["CORTEX_NO_TAINT_ENFORCE"]


@pytest.mark.asyncio
async def test_enforce_taint_check_pii_bleed(sqlite_conn: sqlite3.Connection) -> None:
    os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
    try:
        # Simple plain text host identity bleed
        with pytest.raises(TaintValidationError, match="PII"):
            await enforce_taint_check(sqlite_conn, "token", "My name is Borja Fernandez Angulo")

        # Cyrillic homoglyphs lookalike
        with pytest.raises(TaintValidationError, match="PII"):
            await enforce_taint_check(sqlite_conn, "token", "Bоrja Fеrnandеz") # Cyrillic 'о' and 'е'

        # Base64 encoded PII bleed (use a longer string to exceed base64 alphanumeric length boundary)
        import base64
        b64_pii = base64.b64encode(b"borja fernandez").decode()
        with pytest.raises(TaintValidationError, match="PII"):
            await enforce_taint_check(sqlite_conn, "token", f"obfuscated {b64_pii} value")

        # Hex encoded PII bleed (must encode both parts 'borja fernandez' or similar to trigger proximity/leak check)
        hex_pii = b"borja fernandez".hex()
        with pytest.raises(TaintValidationError, match="PII"):
            await enforce_taint_check(sqlite_conn, "token", f"prefix {hex_pii} suffix")
    finally:
        os.environ["CORTEX_NO_TAINT_ENFORCE"] = "0"


@pytest.mark.asyncio
async def test_enforce_taint_check_anergy(sqlite_conn: sqlite3.Connection) -> None:
    os.environ["CORTEX_NO_TAINT_ENFORCE"] = "0"
    
    # Anergy content checking
    with pytest.raises(TaintValidationError, match="Thermodynamic Violation"):
        await enforce_taint_check(sqlite_conn, "token", "por supuesto aquí tienes el contenido del modelo de lenguaje")


def test_mhc_antigen_router(tmp_path: Path) -> None:
    dynamic_path = tmp_path / "dynamic_antigens.json"
    router = MHCAntigenRouter(dynamic_antigens_path=dynamic_path, promotion_threshold=2)

    # Helper register pattern
    router.register_t_cell("t_cell_1", r"database_init")

    # Present antigen triggers registered cell
    assert router.present_antigen("starting database_init sequence") == "t_cell_1"
    assert router.present_antigen("unrelated query") is None

    # Miss tracking and promotion
    # First miss
    router.record_miss("deploy astro static site", "t_cell_deploy")
    # Present again should still be None
    assert router.present_antigen("deploy astro static site") is None

    # Second miss (hits threshold 2)
    promoted = router.record_miss("deploy astro static site", "t_cell_deploy")
    assert promoted is True

    # Now presenting it should trigger the newly promoted cell
    assert router.present_antigen("deploy astro static site") == "t_cell_deploy"
    assert dynamic_path.exists()
