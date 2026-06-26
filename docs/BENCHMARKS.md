# CORTEX-Persist Reproducible Benchmarks

> **Goal:** Transparency and replicability. All performance claims (~390k agents/sec, O(1) audit verification) must be independently verifiable by anyone using commodity hardware.

## Prerequisites
- Python 3.10+
- `cortex-persist` installed with acceleration: `pip install -e ".[all]"`
- A standard M-series Mac or equivalent Linux machine (16GB RAM minimum).

## Running the Benchmark Suite

We use `pytest-benchmark` to guarantee statistically significant results, avoiding thermal throttling bias.

```bash
# 1. Run the core throughput benchmark
pytest benchmarks/test_throughput.py --benchmark-only --benchmark-columns=mean,stddev,ops

# 2. Run the ledger verification benchmark
pytest benchmarks/test_ledger_crypto.py --benchmark-only
```

## Expected Baselines (M3 Max / 64GB)

| Metric | Condition | Ops/sec | Latency (mean) |
|:-------|:----------|--------:|---------------:|
| **Agent Observation Insert** | Async WAL, Batching=50ms | ~390,000 | 2.5 µs |
| **Merkle Seal Generation** | `hashlib.sha256` | ~120,000 | 8.3 µs |
| **Ed25519 Signature** | `cryptography` lib | ~45,000 | 22.0 µs |
| **Full Auth-Seal Audit** | 100,000 events | N/A | < 1.5 s |

## The "Python Paradox" Mitigation

CORTEX achieves ~390k ops/sec in a Python environment through:
1. **Zero-Copy Memory-Mapped I/O:** Bypassing `read()` syscalls via `mmap_size=20000000000`.
2. **Micro-Batched Asynchronous Merkle Trees:** Cryptographic sealing occurs out-of-band in `batch_window_ms=50`, avoiding the blocking of the main execution loop.
3. **Rust FFI (`cortex_native.cpython-*.so`):** Critical loops and HNSW vector calculations are outsourced to a compiled Rust extension, bypassing the GIL.

If you encounter lower throughput, ensure that the `CORTEX_LEDGER_BATCH_MS` environment variable is tuned to your disk IOPS and that you are using `cortex.db.connect_writer` to manually control WAL checkpoints.
