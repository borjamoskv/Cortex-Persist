# [C5-REAL] Exergy-Maximized Benchmark for CTRE Concurrency
import time

from babylon60.guards.ctre_guard import HAS_RUST_CTRE, CTREGuard


def run_ctre_benchmark(iterations=1000):
    print(f"🚀 Running High-Precision CTRE Benchmarks ({iterations} iterations)...")
    print(f"Rust CTRE FFI available: {HAS_RUST_CTRE}")
    
    expected_hash = 0xABCDEF0123456789
    
    # 1. Matches (No collision) - Rust FFI / CTREGuard
    t0 = time.perf_counter_ns()
    successful_commits = 0
    for _ in range(iterations // 2):
        success, _ = CTREGuard.validate_commit(
            expected_hash=expected_hash,
            current_hash=expected_hash,
            target_x=100.0,
            target_y=200.0
        )
        if success:
            successful_commits += 1
    t1 = time.perf_counter_ns()
    rust_match_total_ns = t1 - t0
    rust_match_avg_ns = rust_match_total_ns / (iterations // 2)

    # 2. Mismatches (Collision) - Rust FFI / CTREGuard
    t0 = time.perf_counter_ns()
    collisions_detected = 0
    for i in range(iterations // 2):
        current_hash = expected_hash + i + 1 # force mismatch
        success, _ = CTREGuard.validate_commit(
            expected_hash=expected_hash,
            current_hash=current_hash,
            target_x=100.0,
            target_y=200.0
        )
        if not success:
            collisions_detected += 1
    t1 = time.perf_counter_ns()
    rust_mismatch_total_ns = t1 - t0
    rust_mismatch_avg_ns = rust_mismatch_total_ns / (iterations // 2)

    # 3. Matches - Python Fallback
    t0 = time.perf_counter_ns()
    for _ in range(iterations // 2):
        CTREGuard._python_fallback(expected_hash, expected_hash)
    t1 = time.perf_counter_ns()
    py_match_total_ns = t1 - t0
    py_match_avg_ns = py_match_total_ns / (iterations // 2)

    # 4. Mismatches - Python Fallback
    t0 = time.perf_counter_ns()
    for i in range(iterations // 2):
        current_hash = expected_hash + i + 1
        CTREGuard._python_fallback(expected_hash, current_hash)
    t1 = time.perf_counter_ns()
    py_mismatch_total_ns = t1 - t0
    py_mismatch_avg_ns = py_mismatch_total_ns / (iterations // 2)

    print("\n## Performance Summary")
    print(f"- Rust FFI Match Avg: {rust_match_avg_ns:.2f} ns ({rust_match_total_ns / 1_000_000:.4f} ms total)")
    print(f"- Rust FFI Collision Avg: {rust_mismatch_avg_ns:.2f} ns ({rust_mismatch_total_ns / 1_000_000:.4f} ms total)")
    print(f"- Python Fallback Match Avg: {py_match_avg_ns:.2f} ns ({py_match_total_ns / 1_000_000:.4f} ms total)")
    print(f"- Python Fallback Collision Avg: {py_mismatch_avg_ns:.2f} ns ({py_mismatch_total_ns / 1_000_000:.4f} ms total)")
    
    print("\n## Collision Verification Summary")
    print(f"- Successful Commits: {successful_commits} / {iterations // 2}")
    print(f"- Collisions Isolated and Rolled Back: {collisions_detected} / {iterations // 2}")
    print(f"- Accuracy: {100.0 * (successful_commits + collisions_detected) / iterations:.1f}%")

if __name__ == "__main__":
    run_ctre_benchmark()
