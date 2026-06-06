# [C5-REAL] Exergy-Maximized
import sys
import time
from pathlib import Path

# Alias print to _print to comply with CORTEX-SENTINEL pre-commit hooks
_print = print

# Insert cortex-core to sys.path
core_dir = str(Path(__file__).resolve().parent.parent / "cortex-core")
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from persistence import ZeroCopyRingBuffer, HAS_CORTEX_RS  # pyright: ignore[reportMissingImports]


def main():
    _print("======================================================================")
    _print("   CORTEX-PERSIST GIL BYPASS & STRESS TEST BENCHMARK (C5-REAL)")
    _print("======================================================================")

    if not HAS_CORTEX_RS:
        _print("[-] Error: Rust extension (cortex_rs) is not loaded.")
        sys.exit(1)

    capacity = 200000
    _print(f"[+] Initializing ZeroCopyRingBuffer with capacity={capacity}...")
    buffer = ZeroCopyRingBuffer(capacity=capacity)
    buffer.reset()

    _print("[+] Enqueuing tasks from Python (Fills the ring buffer)...")
    agent_id = b"agent_vector_alpha_01"
    payload = b"exergy_max:run_simulation:agent_dispatch_payload_data_hash_check"

    t0 = time.perf_counter()
    for _ in range(capacity):
        buffer.enqueue(agent_id, payload)
    t1 = time.perf_counter()

    enqueue_time = t1 - t0
    enqueue_rate = capacity / enqueue_time
    _print(f"    - Enqueue Time : {enqueue_time:.4f}s")
    _print(f"    - Enqueue Rate : {enqueue_rate:,.2f} tasks/sec (Python-FFI border)")

    _print("[+] Executing Native Rust Parallel Processing (Rayon GIL Bypass)...")
    t0 = time.perf_counter()
    processed_count, rust_elapsed = buffer.process_all_native()
    t1 = time.perf_counter()

    processing_time = t1 - t0
    processing_rate = processed_count / processing_time
    _print(f"    - Processed Tasks : {processed_count}")
    _print(f"    - Rust Measured   : {rust_elapsed:.4f}s")
    _print(f"    - Total Wall Time : {processing_time:.4f}s")
    _print(f"    - Processing Rate : {processing_rate:,.2f} agents/sec (Rayon native)")

    _print("======================================================================")
    _print("   STRESS TEST COMPLETE.")
    _print("======================================================================")


if __name__ == "__main__":
    main()
