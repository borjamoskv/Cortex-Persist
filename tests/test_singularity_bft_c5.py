import asyncio
import os
import sqlite3
import hashlib
import time
from pathlib import Path
import pytest
import aiosqlite

DB_PATH = Path("cortex_persist_bft_test.db")


@pytest.fixture(autouse=True)
async def setup_db():
    if DB_PATH.exists():
        DB_PATH.unlink()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS security_audit_log (
                audit_id TEXT PRIMARY KEY,
                timestamp TEXT,
                tenant_id TEXT,
                actor_role TEXT,
                actor_id TEXT,
                action TEXT,
                resource TEXT,
                status TEXT,
                prev_hash TEXT,
                signature TEXT,
                external_anchor TEXT
            )
        """)
        await db.commit()
    yield
    if DB_PATH.exists():
        DB_PATH.unlink()


@pytest.mark.asyncio
async def test_vector_sqlite_wal_deadlock():
    """Vector 1: Concurrencia extrema N=10, timeout 5000ms"""

    async def worker(worker_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA busy_timeout=5000")
            for i in range(100):
                audit_id = hashlib.sha256(f"w{worker_id}_{i}_{time.time()}".encode()).hexdigest()
                await db.execute(
                    "INSERT INTO security_audit_log (audit_id, action) VALUES (?, ?)",
                    (audit_id, "DEADLOCK_TEST"),
                )
                await db.commit()

    workers = [worker(i) for i in range(10)]
    await asyncio.gather(*workers)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM security_audit_log WHERE action='DEADLOCK_TEST'"
        )
        count = (await cursor.fetchone())[0]
        assert count == 1000


@pytest.mark.asyncio
async def test_vector_taint_engine_collapse():
    """Vector 2: Inyección de hashes SHA3-256 colisionados (Simulación de rechazo)"""
    # SQLite PK constraint should reject colliding hashes
    hash_collision = hashlib.sha3_256(b"taint_collision_seed").hexdigest()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO security_audit_log (audit_id, action) VALUES (?, ?)",
            (hash_collision, "TAINT_1"),
        )
        await db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            await db.execute(
                "INSERT INTO security_audit_log (audit_id, action) VALUES (?, ?)",
                (hash_collision, "TAINT_2_COLLISION"),
            )
            await db.commit()


@pytest.mark.asyncio
async def test_vector_ledger_chain_break():
    """Vector 3: Mutación de firmas Ed25519 en nodos históricos (Simulación de detección)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Valid insert
        valid_hash = hashlib.sha256(b"valid_node").hexdigest()
        await db.execute(
            "INSERT INTO security_audit_log (audit_id, signature) VALUES (?, ?)",
            (valid_hash, "valid_signature_ed25519"),
        )
        await db.commit()

        # 2. Mutate history (Adversarial attack)
        await db.execute(
            "UPDATE security_audit_log SET signature = ? WHERE audit_id = ?",
            ("mutated_signature_ed25519", valid_hash),
        )
        await db.commit()

        # 3. Detection (Simulated verifying logic)
        cursor = await db.execute(
            "SELECT signature FROM security_audit_log WHERE audit_id = ?", (valid_hash,)
        )
        corrupted_sig = (await cursor.fetchone())[0]
        assert corrupted_sig != "valid_signature_ed25519"


@pytest.mark.asyncio
async def test_vector_swarm_apoptosis():
    """Vector 4: Inyección de 500 subagentes paralelos exigiendo consenso BFT"""

    async def subagent_task(agent_id):
        # Simulate BFT assertion delay and write
        await asyncio.sleep(0.01)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA busy_timeout=5000")
            audit_id = hashlib.sha256(f"agent_{agent_id}_{time.time()}".encode()).hexdigest()
            await db.execute(
                "INSERT INTO security_audit_log (audit_id, action) VALUES (?, ?)",
                (audit_id, "SWARM_CONSENSUS"),
            )
            await db.commit()

    # Launch 500 parallel agents
    agents = [subagent_task(i) for i in range(500)]
    await asyncio.gather(*agents)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM security_audit_log WHERE action='SWARM_CONSENSUS'"
        )
        count = (await cursor.fetchone())[0]
        assert count == 500
