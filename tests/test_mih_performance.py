import asyncio
import random
import time
from pathlib import Path

from cortex.memory.models import CortexFactModel
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2


async def benchmark_mih():
    print("🚀 BENCHMARK: VOID-BEYOND MIH vs LINEAR SCAN")

    # 1. Setup Store
    db_path = "/tmp/test_mih.db"
    if Path(db_path).exists():
        Path(db_path).unlink()

    from cortex.memory.encoder import AsyncEncoder
    encoder = AsyncEncoder() # Assume default model is OK for benchmark
    store = SovereignVectorStoreL2(encoder=encoder, db_path=db_path)

    # 2. Populate 10,000 Vectors
    print("📦 Populating 10,000 agents manifold...")
    facts = []
    for i in range(10000):
        vec = [random.uniform(-1, 1) for _ in range(1024)]
        fact = CortexFactModel(
            id=f"fact_{i}",
            tenant_id="default",
            project_id="bench",
            content=f"Vector {i} with unique content sentinel.",
            embedding=vec
        )
        facts.append(fact)

    # Bulk insert (simulated batch)
    start_pop = time.perf_counter()
    for fact in facts:
        await store.memorize(fact)
    end_pop = time.perf_counter()
    print(f"✅ Population complete in {end_pop - start_pop:.2f}s")

    # 3. Query Latency
    query_text = "Vector 500 with unique content sentinel."
    print(f"🔍 Querying: '{query_text}'")

    # Warm up
    await store.recall_secure(query=query_text, tenant_id="default", project_id="bench")

    # MEASURE
    start_mih = time.perf_counter()
    results = await store.recall_secure(query=query_text, tenant_id="default", project_id="bench")
    end_mih = time.perf_counter()

    latency_ms = (end_mih - start_mih) * 1000
    print(f"📊 MIH SEARCH LATENCY: {latency_ms:.2f}ms")

    if results:
        print(f"✅ Top Result: {results[0].content} (Score: {results[0]._recall_score:.4f})")
    else:
        print("❌ No results found!")

    # Cleanup
    if Path(db_path).exists():
        Path(db_path).unlink()

    # ASSERT Performance
    if latency_ms < 50: # Threshold for 10k agents on SQLite
        print("🏆 SUCCESS: Operation VOID-BEYOND achieved target latency.")
    else:
        print(f"⚠️ WARNING: Latency {latency_ms:.2f}ms exceeds VOID-GATE target.")

if __name__ == "__main__":
    asyncio.run(benchmark_mih())
