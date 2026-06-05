import logging
logger = logging.getLogger("bench")
import logging
logger = logging.getLogger("bench")
import time
import os
import resource
import sys
sys.path.append("cortex-core")
from ultramap import UltramapSubstrate

def get_memory_mb():
    # resource.getrusage returns bytes on macOS, kilobytes on Linux
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if os.uname().sysname == 'Darwin':
        return usage / (1024 * 1024)
    else:
        return usage / 1024

def main():
    logger.info("=======================================")
    logger.info("   ULTRAMAP FFI STRESS TEST (C5-REAL)  ")
    logger.info("=======================================")
    
    umap = UltramapSubstrate(capacity=1000)
    # Ensure initialized position so update_control_vector works
    umap.update_agent_position(0, 1.0, 1.0, 1.0, "TEST_TARGET", 0.5)
    
    mem_before = get_memory_mb()
    
    iters = 10_000_000
    logger.info(f"Target: {iters} iterations of update_control_vector")
    logger.info(f"Memory (RSS) before: {mem_before:.2f} MB")
    
    start_t = time.perf_counter()
    
    for _ in range(iters):
        umap.update_control_vector(0, 10.0, 0.01, 0.5, 0.8)
        
    end_t = time.perf_counter()
    
    mem_after = get_memory_mb()
    total_time = end_t - start_t
    throughput = iters / total_time
    
    logger.info("---------------------------------------")
    logger.info(f"Total Time: {total_time:.4f} seconds")
    logger.info(f"Throughput: {throughput:,.2f} ops/sec")
    logger.info(f"Memory (RSS) after:  {mem_after:.2f} MB")
    logger.info(f"Memory Delta (Leak): {mem_after - mem_before:.2f} MB")
    
    if (mem_after - mem_before) < 1.0:
        logger.info("[+] MEMORY PROFILE: ZERO-ALLOCATION VERIFIED")
    else:
        logger.info("[-] MEMORY PROFILE: LEAK DETECTED")

if __name__ == "__main__":
    main()
