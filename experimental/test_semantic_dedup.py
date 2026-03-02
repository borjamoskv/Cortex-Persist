import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cortex.engine_async import AsyncCortexEngine
from cortex.database.pool import CortexConnectionPool

async def run_test():
    print("--- V8 Semantic Deduplication Integration Test ---")
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    pool = CortexConnectionPool(db_path)
    engine = AsyncCortexEngine(pool=pool, db_path=db_path)
    
    # Initialize the memory manager to grant L2 vector access
    from cortex.memory.manager import MemoryManager
    engine._memory_manager = MemoryManager(db_path=db_path, enable_vectors=True)
    engine._vec_available = True
    
    fact_1 = "The Alpha algorithm uses advanced hyperbolic gradient descent to minimize loss."
    fact_2 = "By utilizing hyperbolic gradient descent, the Alpha model achieves minimal loss during training."
    
    print(f"\n[Insert 1] Base: '{fact_1}'")
    id_1 = await engine.store(
        project="v8_dedup_test", 
        content=fact_1,
        fact_type="knowledge",
        commit=True
    )
    print(f"-> Fact 1 ID: {id_1}")
    
    print("\n⏳ Permitiendo sincronización del índice vectorial L2 (3s)...")
    await asyncio.sleep(3.0) 
    
    print(f"\n[Insert 2] Parafraseado: '{fact_2}'")
    id_2 = await engine.store(
        project="v8_dedup_test", 
        content=fact_2,
        fact_type="knowledge",
        commit=True
    )
    print(f"-> Fact 2 ID: {id_2}")
    
    if id_1 == id_2:
        print("\n✅ V8 GOVERNANCE SUCCESS: El duplicado semántico ha sido bloqueado con precisión quirúrgica.")
    else:
        print(f"\n❌ FATAL: Deduplicación V8 evadida. ID_1: {id_1} | ID_2: {id_2}")
        
    await engine._memory_manager.close()
    await pool.close()

if __name__ == "__main__":
    asyncio.run(run_test())
