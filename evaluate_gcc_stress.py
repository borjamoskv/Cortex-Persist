import asyncio
import random
import json
import logging
import os
import aiosqlite

from cortex.ledger.causal_graph import CausalGraph
from cortex.engine.causal_scheduler import CausalScheduler
from cortex.engine.rollback_engine import CausalRollbackEngine
from cortex.ledger.execution_trace import ExecutionTraceLedger

logging.basicConfig(level=logging.WARNING)

DB_PATH = "/tmp/gcc_stress.db"

async def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    async with aiosqlite.connect(DB_PATH) as conn:
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
        await conn.execute("CREATE TABLE IF NOT EXISTS thermodynamics_state (tenant_id TEXT PRIMARY KEY, entropy_budget REAL)")
        await conn.commit()

import uuid

async def inject_noise(db_path: str, intensity: float):
    """
    Introduce eventos causales inconsistentes:
    - nodos sin padre válido
    - eventos huérfanos reactivados
    """
    async with aiosqlite.connect(db_path) as conn:
        for _ in range(int(random.random() * 50 * intensity)):
            node_id = f"ghost_{uuid.uuid4().hex[:8]}"
            cost = random.uniform(0.1, 10.0)
            broken_parent = random.choice([True, False])
            
            lineage = []
            if broken_parent:
                # Simulamos dependencia de un nodo muerto para colapsar el CF
                parent_id = f"dead_{random.randint(0, 100)}"
                lineage.append(parent_id)
                # Ensure the dead parent exists as rolled_back
                await conn.execute(
                    "INSERT OR IGNORE INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (parent_id, "default", "noise", 1.0, "[]", "rolled_back", False)
                )
                
            outcome = "crystallized" if random.random() > 0.2 else "rolled_back"
            
            await conn.execute(
                "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (node_id, "default", "noise_injector", cost, json.dumps(lineage), outcome, True)
            )
        await conn.commit()

async def stress_tick(scheduler, db_path, iterations=1000):
    stats = {
        "CF": [],
        "EB": [],
        "rollbacks": 0,
        "coherence_locks": 0,
        "collapse_events": 0,
        "ticks": 0
    }

    print("Iniciando tortura ontologica (CF / EB)...")
    for t in range(iterations):
        stats["ticks"] += 1
        await inject_noise(db_path, intensity=random.uniform(0.1, 0.8))

        tick_result = await scheduler.tick_and_act(window_seconds=3600)
        state = tick_result["tick_state"]
        
        mode = state["execution_mode"]
        cf = state["cf"]
        eb = state["eb"]
        
        stats["CF"].append(cf)
        stats["EB"].append(eb)
        
        if mode == "collapse_prevent":
            stats["rollbacks"] += len(tick_result.get("actions", []))
        elif mode == "coherence_lock":
            stats["coherence_locks"] += 1
        elif mode == "chaotic_irreversible":
            stats["collapse_events"] += 1
            print(f"!!! COLAPSO IRREVERSIBLE en tick {t} | EB: {eb:.2f} | CF: {cf:.2f}")
            break

        if t % 100 == 0:
            print(f"Tick {t:4d} | Mode: {mode:18s} | CF: {cf:.3f} | EB: {eb:.1f}")

    return stats

async def main():
    await init_db()
    
    ledger = ExecutionTraceLedger(DB_PATH)
    graph = CausalGraph(DB_PATH)
    rollback = CausalRollbackEngine(DB_PATH, ledger, None)  # cost_field no es critico para el MVP del test
    scheduler = CausalScheduler(graph, rollback, ledger)
    
    report = await stress_tick(scheduler, DB_PATH, iterations=5000)
    
    print("\n" + "="*50)
    print("STRESS REPORT:")
    print(f"Ticks sobrevivientes : {report['ticks']}")
    print(f"Macro-Rollbacks      : {report['rollbacks']}")
    print(f"Coherence Locks      : {report['coherence_locks']}")
    print(f"Eventos de Colapso   : {report['collapse_events']}")
    
    if report["CF"]:
        print(f"CF final / max / min : {report['CF'][-1]:.3f} / {max(report['CF']):.3f} / {min(report['CF']):.3f}")
    if report["EB"]:
        print(f"EB final / max / min : {report['EB'][-1]:.1f} / {max(report['EB']):.1f} / {min(report['EB']):.1f}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
