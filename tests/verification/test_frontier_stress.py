# [C5-REAL] Exergy-Maximized
"""
Red Team Stress Testing Suite for Causal Graph and Audit Ledger.

Simulates Byzantine failures, state collisions, and high-concurrency race conditions.
Ensures production-level load stability and determinism under pressure.
"""

import asyncio
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.causal.taint_engine import (
    TaintValidationError,
    generate_secure_taint_token,
    enforce_taint_check,
)
from cortex.guards.contradiction_guard import detect_contradictions


# Configure tests
pytestmark = [pytest.mark.asyncio, pytest.mark.slow]
CONCURRENCY_LEVEL = 20


@pytest.fixture
async def engine(tmp_path: Path):
    """Initialize a clean test instance of the CortexEngine."""
    from cortex.engine import CortexEngine

    db = str(tmp_path / "test_stress_frontier.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()

    yield e
    await e.close()


@pytest.fixture
async def ledger_db(tmp_path: Path):
    """Provide a database connection for the Ledger tests."""
    db_path = tmp_path / "test_ledger_stress.db"
    async with aiosqlite.connect(db_path) as conn:
        yield conn


# ─── 1. Ledger Concurrency Bombing (State Collision Test) ───────────────


async def test_ledger_concurrency_bombing(ledger_db):
    """
    Simulates N concurrent agents writing to the EnterpriseAuditLedger.
    Verifies that the hash-chain remains continuous and exactly N records are logged.
    """
    ledger = EnterpriseAuditLedger(ledger_db)
    try:
        await ledger.ensure_table()

        # Pre-generate tasks to blast them concurrently
        async def blast_ledger(agent_id: int):
            return await ledger.log_action(
                tenant_id="default",
                actor_role="agent",
                actor_id=f"agent_{agent_id}",
                action="STRESS_TEST",
                resource=f"resource_{agent_id}",
            )

        tasks = [blast_ledger(i) for i in range(CONCURRENCY_LEVEL)]
        start_time = time.monotonic()

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.monotonic()

        # Ensure no exceptions were raised
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(failures) == 0, f"Concurrency bombing failed: {failures}"
        assert len(results) == CONCURRENCY_LEVEL

        # Verify the hash chain continuity (Merkle Blocks)
        async with ledger_db.execute(
            "SELECT audit_id, prev_hash, signature FROM security_audit_log ORDER BY rowid ASC"
        ) as cursor:
            rows = await cursor.fetchall()

        assert len(rows) == CONCURRENCY_LEVEL

        # Group into blocks
        blocks = []
        current_block = []
        current_sig = rows[0][2] if rows else None

        for row in rows:
            if row[2] != current_sig:
                blocks.append(current_block)
                current_block = [row]
                current_sig = row[2]
            else:
                current_block.append(row)
        if current_block:
            blocks.append(current_block)

        current_hash = "GENESIS"
        for block in blocks:
            # All items in a block must have the same prev_hash and signature
            prev_hash = block[0][1]
            signature = block[0][2]
            assert prev_hash == current_hash, (
                f"Merkle Block Hash chain broken! Expected prev: {current_hash}, got: {prev_hash}"
            )
            for row in block:
                assert row[1] == prev_hash, "Inconsistent prev_hash within block"
                assert row[2] == signature, "Inconsistent signature within block"

            # Verify cryptographic integrity of the block
            batch_audit_ids = [row[0] for row in block]
            from cortex.audit.smt import SparseMerkleTree

            local_smt = SparseMerkleTree()
            for aid in batch_audit_ids:
                local_smt.update(hashlib.sha256(aid.encode()).hexdigest(), aid)
            merkle_root = local_smt.root
            entry_hash = hashlib.sha256(
                f"merkle_batch:{merkle_root}:{prev_hash}".encode()
            ).hexdigest()

            assert ledger.verify_zk_seal(entry_hash, signature), (
                "Invalid ZK seal/signature on Merkle Block"
            )

            current_hash = entry_hash

        # Verify the last hash of the object is correctly updated
        assert ledger._last_hash == current_hash
        print(
            f"\n[Ledger] Processed {CONCURRENCY_LEVEL} concurrent writes into {len(blocks)} Merkle Blocks in {end_time - start_time:.3f}s"
        )
    finally:
        await ledger.close()


# ─── 2. Byzantine Taint Tsunami (Nonce & Replay attacks) ───────────────


async def test_byzantine_taint_tsunami(ledger_db, monkeypatch):
    """
    Barrages the TaintEngine with valid and invalid taint tokens concurrently.
    Verifies that replay attacks (reused nonces) and invalid signatures are deterministically rejected.
    """
    import base64

    # Setup agent key
    priv_key = Ed25519PrivateKey.generate()
    priv_key_bytes = priv_key.private_bytes(
        encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.Raw,
        format=__import__("cryptography").hazmat.primitives.serialization.PrivateFormat.Raw,
        encryption_algorithm=__import__(
            "cryptography"
        ).hazmat.primitives.serialization.NoEncryption(),
    )
    priv_key_b64 = base64.b64encode(priv_key_bytes).decode("ascii")

    pub_key_bytes = priv_key.public_key().public_bytes(
        encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.Raw,
        format=__import__("cryptography").hazmat.primitives.serialization.PublicFormat.Raw,
    )
    pub_key_b64 = base64.b64encode(pub_key_bytes).decode("ascii")

    # Seed the agent in the DB
    await ledger_db.execute(
        "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, public_key TEXT, is_active INTEGER)"
    )
    await ledger_db.execute(
        "INSERT INTO agents (id, public_key, is_active) VALUES (?, ?, 1)",
        ("agent_byz", pub_key_b64),
    )
    await ledger_db.commit()

    content = "Adversarial Test Content"
    valid_nonce = "valid_nonce_01"

    # 1 valid token
    valid_token = generate_secure_taint_token(
        agent_id="agent_byz",
        session_id="sess_1",
        content=content,
        private_key_b64=priv_key_b64,
        nonce=valid_nonce,
    )

    # Reused nonce
    replayed_token = generate_secure_taint_token(
        agent_id="agent_byz",
        session_id="sess_1",
        content=content,
        private_key_b64=priv_key_b64,
        nonce=valid_nonce,  # Reuse the exact same nonce!
    )

    # Invalid signature
    invalid_token = valid_token[:-5] + "XXXXX"

    # Ensure enforcement is not bypassed for this test
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "0")

    async def attempt_taint(token):
        try:
            await enforce_taint_check(ledger_db, token, content)
            return True
        except TaintValidationError:
            return False

    # Blast concurrently: 1 valid, 50 replayed, 49 invalid signatures
    tasks = [attempt_taint(valid_token)]
    tasks.extend([attempt_taint(replayed_token) for _ in range(CONCURRENCY_LEVEL // 2)])
    tasks.extend([attempt_taint(invalid_token) for _ in range(CONCURRENCY_LEVEL // 2 - 1)])

    results = await asyncio.gather(*tasks)

    # Only EXACTLY ONE request should pass (the first one to grab the nonce)
    # The others must fail due to Replay Attack (nonce already used) or invalid signature
    successful_attempts = sum(results)
    assert successful_attempts == 1, (
        f"Expected exactly 1 successful taint validation, got {successful_attempts}"
    )


# ─── 3. Contradiction Collisions (Causal Graph Stress) ──────────────────


async def test_contradiction_collisions(engine):
    """
    Pushes opposing/colliding facts to the memory system concurrently.
    Verifies the system detects contradictions successfully without race condition deadlocks.
    """

    # We will bombard the engine with slightly varying but opposing contents.
    # The contradiction detector relies on vector search and exact match overlapping logic.
    # We test `detect_contradictions` under high load.

    project = "collision_test"
    base_truth = "The protocol strictly uses Ed25519."

    # Seed truth
    await engine.store(
        project=project,
        content=base_truth,
        fact_type="decision",
        source="system",
        archaeology_audited=True,
    )

    # We prepare tasks to detect contradiction simultaneously against this base truth.
    adversarial_claim = "The protocol strictly uses RSA."

    async def blast_contradiction():
        report = await detect_contradictions(
            new_content=adversarial_claim,
            new_project=project,
            db_path=str(engine._db_path),
        )
        return report

    tasks = [
        blast_contradiction() for _ in range(20)
    ]  # Contradiction uses LLM/embeddings, limit concurrency for tests to avoid API limits if mocked
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify no deadlocks/exceptions and contradictions found
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(failures) == 0, f"Contradiction detection failed: {failures}"

    for report in results:
        assert getattr(report, "has_conflicts", False) is True, (
            "Contradiction failed to trigger during concurrent execution"
        )
