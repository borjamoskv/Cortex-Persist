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

# Silenciar logs que no sean críticos
logging.getLogger("cortex").setLevel(logging.CRITICAL)

DB_PATH = "/tmp/cortex_survivor.db"

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

async def inject_noise(db_path: str, tenant_id: str, intensity: float):
    # Inyecta nodos muertos para destrozar el CF y restaura EB
    async with aiosqlite.connect(db_path, timeout=10) as conn:
        for _ in range(int(max(1, random.random() * 50 * intensity))):
            node_id = f"ghost_{uuid.uuid4().hex[:8]}"
            cost = random.uniform(0.1, 10.0)
            
            parent_id = f"dead_{random.randint(0, 1000)}_{tenant_id}"
            lineage = [parent_id]
            await conn.execute(
                "INSERT OR IGNORE INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (parent_id, tenant_id, "noise", 1.0, "[]", "rolled_back", False)
            )
                
            await conn.execute(
                "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (node_id, tenant_id, "noise_injector", cost, json.dumps(lineage), "crystallized", True)
            )
            
        await conn.execute("UPDATE thermodynamics_state SET entropy_budget = entropy_budget - ? WHERE tenant_id = ?", (random.uniform(50, 600), tenant_id))
        await conn.commit()

async def inject_clean_mutations(db_path: str, tenant_id: str):
    # Inyecta nodos cristalizados y eleva EB (Aporta valor)
    async with aiosqlite.connect(db_path, timeout=10) as conn:
        parent_id = f"base_clean_{tenant_id}"
        await conn.execute(
            "INSERT OR IGNORE INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (parent_id, tenant_id, "clean", 1.0, "[]", "crystallized", False)
        )
        
        for _ in range(5):
            node_id = f"clean_{uuid.uuid4().hex[:8]}"
            cost = random.uniform(0.1, 0.5)
            await conn.execute(
                "INSERT INTO execution_trace_ledger (id, tenant_id, origin, cost, lineage, outcome, rollback_possible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (node_id, tenant_id, "clean_mutation", cost, json.dumps([parent_id]), "crystallized", True)
            )
            
        await conn.execute("UPDATE thermodynamics_state SET entropy_budget = entropy_budget + 100 WHERE tenant_id = ?", (tenant_id,))
        await conn.commit()

async def survivor_test():
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
    for _ in range(9):
        timelines.append(await bifurcation.spawn_timeline("default"))
        
    # Split: 8 Enfermas, 2 Sanas
    sick_timelines = timelines[:8]
    healthy_timelines = timelines[8:]
    
    print("[1] Infectando 8 timelines con ruido estructural...")
    for t in sick_timelines:
        await inject_noise(DB_PATH, t, intensity=2.0)
        
    print("[2] Inyectando mutaciones válidas a 2 timelines sanas...")
    for t in healthy_timelines:
        await inject_clean_mutations(DB_PATH, t)
        
    current_multiverse = await bifurcation.evaluate_multiverse()
    
    print("\n--- MULTIVERSO (Pre-Poda) ---")
    for s in current_multiverse:
        status = "SANA " if s["tenant_id"] in healthy_timelines else "ENFERMA"
        print(f"[{status}] {s['tenant_id']} | CF: {s['cf']:.2f} | EB: {s['eb']:.1f} | Exergy: {s['exergy']:.1f}")
        
    print("\n[3] Invocando ExergyDaemon (Cirugía de Ramas Muertas)...")
    await bifurcation.prune_dead_branches(current_multiverse)
    
    final_multiverse = await bifurcation.evaluate_multiverse()
    
    print("\n--- MULTIVERSO (Post-Poda) ---")
    survivors = [s["tenant_id"] for s in final_multiverse]
    for t in survivors:
        status = "SANA " if t in healthy_timelines else "ENFERMA"
        print(f"[{status}] {t} SOBREVIVIÓ.")
        
    if not survivors:
        print("\n[VERDICT]: FALLO CATASTRÓFICO. El daemon es genocida (Extinción Total).")
        return
        
    if any(t in sick_timelines for t in survivors):
        print("\n[VERDICT]: FALLO. El daemon es blando. Realidades enfermas sobrevivieron.")
        return

    print("\n[VERDICT]: ÉXITO. C6-RESILIENT ALCANZADO. ExergyDaemon opera como cirujano.")

if __name__ == "__main__":
    asyncio.run(survivor_test())
