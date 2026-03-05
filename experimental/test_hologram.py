import asyncio
import time
import os
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.hologram import HolographicMemory
from cortex.embeddings import LocalEmbedder

async def test_hologram():
    print("Setting up test...")
    os.environ["CORTEX_NO_LLM"] = "1"
    
    embedder = LocalEmbedder()
    encoder = AsyncEncoder(embedder)
    
    store = SovereignVectorStoreL2(encoder)
    holo = HolographicMemory(store)
    
    print("Loading hologram matrix...")
    t0 = time.time()
    await holo.initialize()
    t1 = time.time()
    print(f"Loaded {len(holo._metadata)} records in {(t1-t0)*1000:.2f}ms")
    
    print("Benchmarking recall...")
    query = "Zero trust scaling architecture"
    
    t0 = time.time()
    res1 = await store.recall_secure(tenant_id="default", project_id="MOSKV-1", query=query, limit=5)
    t1 = time.time()
    
    t2 = time.time()
    res2 = await holo.recall_holographic(query=query, limit=5, tenant_id="default", project_id="MOSKV-1")
    t3 = time.time()
    
    sql_ms = (t1 - t0) * 1000
    holo_ms = (t3 - t2) * 1000
    
    print("-" * 40)
    print(f"SQL/Disk Recall: {sql_ms:.2f}ms")
    print(f"Hologram Recall: {holo_ms:.2f}ms")
    speedup = sql_ms / holo_ms if holo_ms > 0 else 0
    print(f"Speedup: {speedup:.1f}x")
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_hologram())
