# [C5-REAL] Exergy-Maximized
import time

import numpy as np
from cortex.utils import void_vec

# CORTEX - Operation VOID-MAX: Batch SIMD Benchmark
# Axiom Ω6: Zero-Rhetoric Mandate.


def benchmark():
    count = 1000  # Number of vectors in the batch
    iters = 1000  # Number of total batch operations (1M total comparisons)
    print(f"🚀 VOID-MAX BATCH SIMD BENCHMARK (Batch={count}, Iters={iters})")

    # Generate 1024-bit (128 bytes) vectors
    dim = 1024
    query = void_vec.pack_void_bit(np.random.randn(dim))
    batch = [void_vec.pack_void_bit(np.random.randn(dim)) for _ in range(count)]

    # Phase 1: Python Scalar (Fallback)
    start_py = time.monotonic()
    for _ in range(iters):
        # We manually simulate the sequential call to compare overhead
        [void_vec.void_hamming_dist(query, b) for b in batch]
    end_py = time.monotonic()

    py_time = (end_py - start_py) * 1000
    print(f"🐍 Python (Sequential): {py_time:.2f}ms")

    # Phase 2: Batch SIMD (Neon)
    if not void_vec._accel:
        print("❌ SIMD Accelerator not loaded. Skipping Neon phase.")
    else:
        start_simd = time.monotonic()
        for _ in range(iters):
            void_vec.void_batch_hamming_dist(query, batch)
        end_simd = time.monotonic()

        simd_time = (end_simd - start_simd) * 1000
        print(f"💎 Batch SIMD (Neon ARM64): {simd_time:.2f}ms")
        speedup = py_time / simd_time
        print(f"🏆 SPEEDUP: {speedup:.2f}x improvement.")


if __name__ == "__main__":
    benchmark()
