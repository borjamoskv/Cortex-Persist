import time
import asyncio
import uuid
import aiosqlite
import os

import cortex_rs
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.logic.semantic_crdt import SemanticOrchestrator
from cortex.auth.enterprise_identity import SovereignIdentity

ITERATIONS = 10_000

def bench_rust_init():
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        s = cortex_rs.SemanticState()
    end = time.perf_counter()
    return (end - start) / ITERATIONS

def bench_rust_insert():
    s = cortex_rs.SemanticState()
    uuids = [str(uuid.uuid4()) for _ in range(30)] # Avoid compaction
    
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        s.add_active_support(uuids[0])
    end = time.perf_counter()
    return (end - start) / ITERATIONS

def bench_logop():
    s = cortex_rs.SemanticState()
    s.add_active_support(str(uuid.uuid4()))
    engine = cortex_rs.LogOpEngine()
    
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        engine.resolve_outcome(s)
    end = time.perf_counter()
    return (end - start) / ITERATIONS

async def bench_orchestrator_compaction():
    db_path = "/tmp/cortex_benchmark.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    async with aiosqlite.connect(db_path) as conn:
        ledger = EnterpriseAuditLedger(conn)
        identity = SovereignIdentity(tenant_id="tenant_1", actor_id="bench_bot", role="CRDT_ORCHESTRATOR")
        orchestrator = SemanticOrchestrator(ledger=ledger, identity=identity)
        
        # Fill buffer to exactly 32
        for _ in range(32):
            await orchestrator.add_active_support(str(uuid.uuid4()))
            
        start = time.perf_counter()
        # This insertion will trigger the compaction workflow via Ledger
        await orchestrator.add_active_support(str(uuid.uuid4()))
        end = time.perf_counter()
        return end - start

async def run_all():
    print(f"Running benchmarks ({ITERATIONS} iterations)...")
    
    t_init = bench_rust_init()
    print(f"SemanticState Init: {t_init * 1e6:.2f} µs/op")
    
    t_insert = bench_rust_insert()
    print(f"SemanticState Insert (no compact): {t_insert * 1e6:.2f} µs/op")
    
    t_logop = bench_logop()
    print(f"LogOpEngine Resolution: {t_logop * 1e6:.2f} µs/op")
    
    t_compact = await bench_orchestrator_compaction()
    print(f"Orchestrator + Ledger Compaction Latency: {t_compact * 1000:.2f} ms/op")
    
    print("\nBenchmark complete.")

if __name__ == "__main__":
    asyncio.run(run_all())
