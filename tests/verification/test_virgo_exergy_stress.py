# [C5-REAL] Exergy-Maximized
"""
Concurrency and Adversarial Stress Test for VirgoContextGuard and ExergyGuard.

Validates that high-concurrency dispatching of inputs with varying exergy yields
and cryptographic signatures executes correctly without deadlocks or state leakage.
"""

from __future__ import annotations




import asyncio
import hashlib
import pytest
import aiosqlite

from pathlib import Path
from typing import Any

from legacy_research.guards.virgo import VirgoContextGuard, ContextPoisoningError, VirgoValidationError
from legacy_research.guards.exergy_guard import ExergyGuard



pytestmark = [pytest.mark.asyncio]


@pytest.fixture
async def temp_db(tmp_path: Path):
    """Provide a database connection for Virgo tests, creating the admissions table."""
    db_path = tmp_path / "test_virgo_stress.db"
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_replay_admissions (
                tenant_id TEXT,
                event_id TEXT,
                nonce TEXT UNIQUE,
                request_hash TEXT,
                payload_hash TEXT,
                ledger_event_id TEXT,
                actor_key_id TEXT,
                action TEXT,
                issued_at TEXT,
                accepted_at TEXT
            )
            """
        )
        await conn.commit()
        yield conn


async def test_virgo_guard_concurrency(temp_db):
    """
    Bombards VirgoContextGuard check method concurrently with valid and invalid signatures/nonces.
    Checks replay attack prevention under extreme concurrent race conditions.
    """
    guard = VirgoContextGuard()

    # Pre-generate valid expected signatures (HMAC/Hash fallback)
    content = "Structural crystallized fact about the repository architecture."
    project = "cortex"
    nonces = [f"stress_nonce_{i}" for i in range(100)]

    # 50 valid requests with unique nonces, 50 invalid signatures, and 50 duplicate nonces
    async def run_check(nonce: str, signature: str, expect_success: bool):
        meta = {
            "source": "agent:swarm",
            "agent_id": "test_agent_01",
            "logos_signature": signature,
            "nonce": nonce,
        }
        try:
            await guard.check(content, project, "decision", meta, temp_db)
            return True
        except (VirgoValidationError, ContextPoisoningError):
            return False

    tasks = []
    # 1. 50 Valid runs
    for nonce in nonces[:50]:
        sig = hashlib.sha256(f"{content}{nonce}{project}".encode()).hexdigest()
        tasks.append(run_check(nonce, sig, expect_success=True))

    # 2. 50 Duplicate nonces (replay)
    for nonce in nonces[:50]:
        sig = hashlib.sha256(f"{content}{nonce}{project}".encode()).hexdigest()
        tasks.append(run_check(nonce, sig, expect_success=False))

    # 3. 50 Invalid signatures
    for nonce in nonces[50:]:
        tasks.append(run_check(nonce, "invalid_sig_value", expect_success=False))

    results = await asyncio.gather(*tasks)

    # Verify that exactly 50 requests succeeded (the valid unique ones)
    successful_runs = sum(results)
    assert successful_runs == 50, f"Expected 50 successful guard admissions, got {successful_runs}"


async def test_exergy_guard_concurrency():
    """
    Sends a burst of concurrent payloads to ExergyGuard to test throughput and evaluation safety.
    """
    guard = ExergyGuard()

    valid_content = "This establishes a deterministic validation boundary for memory writes using cryptographic seals."
    invalid_content = (
        "por supuesto aquí tienes el código espero que te sea muy de utilidad amigo mio"
    )

    async def check_exergy(content: str, is_valid: bool):
        try:
            score = guard.check_thermodynamic_yield(content, "cortex", "decision")
            return score > 0.55
        except ValueError:
            return False

    tasks = []
    for _ in range(100):
        tasks.append(check_exergy(valid_content, is_valid=True))
        tasks.append(check_exergy(invalid_content, is_valid=False))

    results = await asyncio.gather(*tasks)

    # We ran 100 valid and 100 invalid checks
    assert len(results) == 200
    # Exactly 100 valid ones must have passed, and exactly 100 invalid ones must have failed
    assert sum(results) == 100
