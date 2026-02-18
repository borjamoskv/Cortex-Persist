import asyncio
import uuid
from pathlib import Path


# Simplified logging for robustness
def log(msg):
    print(f"\033[1;34m[SOVEREIGN]\033[0m {msg}")

from cortex.connection_pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine


async def simulate_consensus():
    # 1. Setup Sandbox
    # Use unique DB to avoid disk I/O errors from locks
    run_id = str(uuid.uuid4())[:8]
    db_path = Path(f"test_consensus_{run_id}.db")

    log("🦅 SOVEREIGN CONSENSUS SIMULATION v1.5 (GOD MODE FINAL PATCH)")
    print(f"📦 Database: {db_path}")
    print("-" * 40)

    # 2. Init Storage
    pool = CortexConnectionPool(str(db_path))
    await pool.initialize()
    engine = AsyncCortexEngine(pool, str(db_path))

    # Init Schema (Minimal for sim)
    async with engine.session() as conn:
        from cortex.schema import ALL_SCHEMA
        # Join all schema parts into one script
        full_schema = "\n".join(ALL_SCHEMA)
        await conn.executescript(full_schema)
        await conn.commit()

    log("Storage & Schema Materialized.")

    try:
        # 3. Create Fact
        print("\n[Step 1] Creating Genesis Fact...")
        fact_id = await engine.store(
            project="simulation",
            content="God Mode is operational within the Sovereign Gate.",
            fact_type="principle",
            tags=["law", "core", "verification"]
        )
        print(f"👉 Fact ID: {fact_id} created.")

        # 4. Register Agents
        agents = {
            "agent_a": 0.8,
            "agent_b": 0.2,
            "agent_c": 0.5
        }

        async with engine.session() as conn:
            for name, score in agents.items():
                await conn.execute(
                    "INSERT INTO agents (id, public_key, name, agent_type, reputation_score) VALUES (?, 'dummy_pk_' || ?, ?, 'ai', ?)",
                    (name, name, name.upper(), score)
                )
            await conn.commit()
        log("Agents Registered.")

        # 5. Vote
        print("\n[Step 2] Executing Consensus Round...")

        s1 = await engine.vote(fact_id, "agent_a", 1)
        print(f"🗳️ Agent A (+1) -> Score: {s1}")

        s2 = await engine.vote(fact_id, "agent_b", -1)
        print(f"🗳️ Agent B (-1) -> Score: {s2}")

        s3 = await engine.vote(fact_id, "agent_c", 1)
        print(f"🗳️ Agent C (+1) -> Score: {s3}")

        # 6. Verify
        print("\n[Step 3] Verifying Ledger Constraints...")

        fact = await engine.get_fact(fact_id)
        if fact:
            print(f"📊 Final Score: {fact['consensus_score']}")
            print(f"🏷️  Confidence: {fact['confidence']}")

            if fact['confidence'] != "verified":
                print("\033[1;31m❌ FAILURE: Fact should be verified (Score > 1.5)\033[0m")
            else:
                print("\033[1;32m✅ SUCCESS: Consensus Reached in God Mode.\033[0m")
        else:
             print("\033[1;31m❌ FAILURE: Fact not found.\033[0m")

        # 7. Audit
        async with engine.session() as conn:
            async with conn.execute("SELECT hash, action, detail FROM transactions ORDER BY id") as cursor:
                rows = await cursor.fetchall()
                print("\n📜 Immutable Ledger Trail:")
                for r in rows:
                    if r[0]:
                        print(f"   [{r[0][:8]}] {r[1]} -> {r[2]}")
                    else:
                        print(f"   [GENESIS ] {r[1]} -> {r[2]}")

    finally:
        await pool.close()
        if db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                print(f"⚠️ Warning: Could not delete {db_path} (still locked?)")

if __name__ == "__main__":
    asyncio.run(simulate_consensus())
