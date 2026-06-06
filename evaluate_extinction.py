import asyncio
import os
import time
import random
import uuid
import json
import logging
import aiosqlite

from cortex.ledger.causal_graph import CausalGraph
from cortex.engine.causal_scheduler import CausalScheduler
from cortex.engine.rollback_engine import CausalRollbackEngine
from cortex.ledger.execution_trace import ExecutionTraceLedger
from cortex.engine.bifurcation_engine import ExergyBifurcationEngine
from cortex.engine.exergy_daemon import ExergyDaemon

# Silenciar logs que no sean críticos
logging.getLogger("cortex").setLevel(logging.CRITICAL)

DB_PATH = "/tmp/cortex_extinction.db"


async def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_trace_ledger (
                id              TEXT PRIMARY KEY,
                tenant_id       TEXT NOT NULL DEFAULT 'default',
                origin          TEXT NOT NULL,
                cost            REAL NOT NULL,
                lineage         TEXT NOT NULL DEFAULT '[]',
                outcome         TEXT NOT NULL,
                rollback_possible BOOLEAN NOT NULL DEFAULT FALSE,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS thermodynamics_state (tenant_id TEXT PRIMARY KEY, entropy_budget REAL)"
        )
        await conn.commit()


async def get_db_size():
    return os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0


async def get_tenants(db_path):
    async with aiosqlite.connect(db_path, timeout=10) as conn:
        cursor = await conn.execute("SELECT DISTINCT tenant_id FROM thermodynamics_state")
        return [row[0] for row in await cursor.fetchall()]


async def inject_noise(db_path: str, tenant_id: str, intensity: float):
    async with aiosqlite.connect(db_path, timeout=10) as conn:
        for _ in range(int(max(1, random.random() * 50 * intensity))):
            node_id = f"ghost_{uuid.uuid4().hex[:8]}"
            cost = random.uniform(0.1, 10.0)
            broken_parent = random.choice([True, False])

            lineage = []
            if broken_parent:
                parent_id = f"dead_{random.randint(0, 1000)}_{tenant_id}"
                lineage.append(parent_id)
                await conn.execute(
                    "INSERT OR IGNORE INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (parent_id, tenant_id, "noise", 1.0, "[]", "rolled_back", False),
                )

            outcome = "crystallized" if random.random() > 0.2 else "rolled_back"

            await conn.execute(
                "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (node_id, tenant_id, "noise_injector", cost, json.dumps(lineage), outcome, True),
            )

        # Simular deuda térmica severa restando del Entropy Budget masivamente
        await conn.execute(
            "UPDATE thermodynamics_state SET entropy_budget = entropy_budget - ? WHERE tenant_id = ?",
            (random.uniform(50, 600), tenant_id),
        )
        await conn.commit()


async def mass_extinction_test():
    await init_db()

    ledger = ExecutionTraceLedger(DB_PATH)
    graph = CausalGraph(DB_PATH)
    rollback = CausalRollbackEngine(DB_PATH, ledger, None)
    scheduler = CausalScheduler(graph, rollback, ledger)
    bifurcation = ExergyBifurcationEngine(ledger, scheduler)

    print("[1] Forjando 10 timelines iniciales...")
    async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
        await conn.execute(
            "INSERT INTO thermodynamics_state (tenant_id, entropy_budget) VALUES ('default', 1000.0)"
        )
        await conn.commit()

    timelines = ["default"]
    for _ in range(9):
        new_tl = await bifurcation.spawn_timeline("default")
        timelines.append(new_tl)

    db_size_before = await get_db_size()
    multiverse = await bifurcation.evaluate_multiverse()
    avg_fitness_before = sum(t["exergy"] for t in multiverse) / len(multiverse)

    print(f"    - Timelines: {len(timelines)}")
    print(f"    - Avg Fitness inicial: {avg_fitness_before:.2f}")

    print("\n[2] Desatando Macro-Bug de Explosión Combinatoria y Poda Secuencial...")
    total_spawned = 10
    start_time = time.time()

    # Tormenta termodinámica de 100 ticks (aprox 10 segundos de asedio total)
    for _tick in range(100):
        current_tenants = await get_tenants(DB_PATH)
        if not current_tenants:
            # Extinción total
            break

        # 1. Macro-Bug: Inyectar ruido y deuda a TODOS los universos vivos simultáneamente
        for t in current_tenants:
            await inject_noise(DB_PATH, t, intensity=2.0)

        # 2. Daemon evalúa multiverso y aplica guadaña (simula el daemon asíncrono)
        current_multiverse = await bifurcation.evaluate_multiverse()
        await bifurcation.prune_dead_branches(current_multiverse)

        # 3. Explosión Reproductiva: Universos esquizofrénicos (CF bajo) se replican
        for state in current_multiverse:
            if state["exergy"] > 0 and state["cf"] < 0.8:  # Umbral de enfermedad
                await bifurcation.spawn_timeline(state["tenant_id"])
                total_spawned += 1

        await asyncio.sleep(0.01)

    end_time = time.time()

    print("\n[3] Estabilizando y Midiendo Secuelas...")
    final_multiverse = await bifurcation.evaluate_multiverse()
    timeline_count_after = len(final_multiverse)
    dead_timelines_removed = total_spawned - timeline_count_after

    avg_fitness_after = (
        sum(t["exergy"] for t in final_multiverse) / timeline_count_after
        if timeline_count_after > 0
        else 0
    )
    db_size_after = await get_db_size()

    # Calcular Exergy Recuperado (Asumiendo 1000 base - deuda de las purgadas)
    exergy_recovered = dead_timelines_removed * 1000

    print("\n" + "=" * 50)
    print("THERMODYNAMIC MASS EXTINCTION REPORT:")
    print("timeline_count_before    : 10")
    print(f"total_timelines_spawned  : {total_spawned}")
    print(f"timeline_count_after     : {timeline_count_after}")
    print(f"dead_timelines_removed   : {dead_timelines_removed}")
    print(f"average_fitness_before   : {avg_fitness_before:.2f}")
    print(f"average_fitness_after    : {avg_fitness_after:.2f}")
    print(f"db_size_before           : {db_size_before / 1024:.2f} KB")
    print(f"db_size_after            : {db_size_after / 1024:.2f} KB")
    print(f"collapse_latency_ms      : {(end_time - start_time) * 1000:.1f} ms")
    print(f"exergy_recovered         : ~{exergy_recovered:.1f} (deuda colapsada)")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(mass_extinction_test())
