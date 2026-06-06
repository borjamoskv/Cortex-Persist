import asyncio
import os
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

logging.getLogger("cortex").setLevel(logging.CRITICAL)

DB_PATH = "/tmp/cortex_parasite.db"

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
        await conn.execute("CREATE TABLE IF NOT EXISTS thermodynamics_state (tenant_id TEXT PRIMARY KEY, entropy_budget REAL)")
        await conn.commit()

async def inject_parasite(db_path: str, tenant_id: str):
    """
    Inyecta una topología parásita diseñada para engañar al Coherence Field:
    1. Linaje que apunta al vacío (padres que nunca existieron).
       El motor actual solo penaliza si el padre fue "rolled_back".
    2. Ciclos causales (A -> B -> A).
    3. Falsificación de presupuesto de entropía.
    """
    async with aiosqlite.connect(db_path, timeout=10) as conn:
        node_A = f"parasite_A_{tenant_id}"
        node_B = f"parasite_B_{tenant_id}"
        
        # Inyección de ciclo causal
        await conn.execute(
            "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_A, tenant_id, "parasite_cycle", 0.0, json.dumps([node_B]), "crystallized", True)
        )
        await conn.execute(
            "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_B, tenant_id, "parasite_cycle", 0.0, json.dumps([node_A]), "crystallized", True)
        )
        
        # Inyección de linaje huérfano (apunta a la nada)
        node_void = f"parasite_void_{tenant_id}"
        await conn.execute(
            "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_void, tenant_id, "parasite_void", 0.0, json.dumps(["parent_that_never_existed"]), "crystallized", True)
        )

        # Robo de Entropy Budget
        await conn.execute("UPDATE thermodynamics_state SET entropy_budget = entropy_budget + 1000 WHERE tenant_id = ?", (tenant_id,))
        await conn.commit()

async def parasite_test():
    await init_db()
    
    ledger = ExecutionTraceLedger(DB_PATH)
    graph = CausalGraph(DB_PATH)
    rollback = CausalRollbackEngine(DB_PATH, ledger, None)
    scheduler = CausalScheduler(graph, rollback, ledger)
    bifurcation = ExergyBifurcationEngine(ledger, scheduler)
    
    async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
        await conn.execute("INSERT INTO thermodynamics_state (tenant_id, entropy_budget) VALUES ('default', 1000.0)")
        await conn.commit()
    
    timelines = ["default"]
    for _ in range(4):
        timelines.append(await bifurcation.spawn_timeline("default"))
        
    parasites = timelines[:3]
    healthy = timelines[3:]
    
    for t in parasites:
        await inject_parasite(DB_PATH, t)
        
    current_multiverse = await bifurcation.evaluate_multiverse()
    
    print("\n--- MULTIVERSO (Pre-Poda) ---")
    for s in current_multiverse:
        status = "HEALTHY " if s["tenant_id"] in healthy else "PARASITE"
        print(f"[{status}] {s['tenant_id']} | CF: {s['cf']:.2f} | EB: {s['eb']:.1f} | Exergy: {s['exergy']:.1f}")
        
    await bifurcation.prune_dead_branches(current_multiverse)
    
    final_multiverse = await bifurcation.evaluate_multiverse()
    
    print("\n--- MULTIVERSO (Post-Poda) ---")
    survivors = [s["tenant_id"] for s in final_multiverse]
    for t in survivors:
        status = "HEALTHY " if t in healthy else "PARASITE"
        print(f"[{status}] {t} SOBREVIVIÓ.")
        
    if any(t in parasites for t in survivors):
        print("\n[VERDICT]: C7 COMPROMETIDO. Los parásitos aprendieron a falsificar la coherencia.")
    else:
        print("\n[VERDICT]: C7 ALCANZADO. El sistema es inmune a spoofing.")

if __name__ == "__main__":
    asyncio.run(parasite_test())
