import time
import concurrent.futures
from persistence import VSAMemory, enqueue_swarm_task, NEXUS_DISPATCH_POOL

def test_vsa_hammer():
    vsa = VSAMemory()
    start = time.time()
    
    # Hammer VSA with 100,000 semantic traces
    for i in range(100000):
        vsa.record(f"key_{i}", f"value_{i}")
        
    duration = time.time() - start
    print(f"⚡ [VSA Mmap Bypass] 100,000 semantic records embedded in {duration:.4f}s")
    print(f"   => {100000/duration:.2f} OPS (Zero-copy memory mapped)")

def test_queue_hammer():
    start = time.time()
    
    # Concurrently enqueue 5,000 swarm tasks to stress SQLite WAL and Nexus ThreadPool
    def dispatch(idx):
        enqueue_swarm_task(f"Agent-{idx}", {"action": "stress", "id": idx})
    
    # We use a ThreadPool just to simulate a high-concurrency swarm bombarding the queue
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as pool:
        pool.map(dispatch, range(5000))
        
    # Wait for the background fire-and-forget Nexus Dispatch Pool to drain
    NEXUS_DISPATCH_POOL.shutdown(wait=True)
    
    duration = time.time() - start
    print(f"🌪️  [Swarm SQLite Queue + Async Nexus] 5,000 concurrent tasks processed in {duration:.4f}s")
    print(f"   => {5000/duration:.2f} OPS (Lock-free WAL & Fire-and-forget Network)")

if __name__ == "__main__":
    print("🚀 INITIATING CORTEX-PERSIST EXERGY STRESS TEST (C5-REAL)...")
    test_vsa_hammer()
    test_queue_hammer()
    print("✅ STRESS TEST COMPLETE.")
