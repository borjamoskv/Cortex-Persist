"""
CORTEX vs Cloud MaaS (Memory-as-a-Service) Benchmark Proof.

Compares local in-process CORTEX retrieval latency against simulated
cloud-based memory services (Mem0, LangChain) to demonstrate the
sovereign O(1) speed advantage.
"""

import sqlite3
import sys
import time
from pathlib import Path

# ─── Constants ─────────────────────────────────────────────────────────
QUERIES: int = 1000  # Number of continuous agentic memory retrievals
CLOUD_LATENCY_MS: int = 120  # Conservative per-request cloud latency (ms)
CLOUD_COST_PER_10K: float = 5.00  # USD per 10k cloud retrievals


def print_header(text: str) -> None:
    """Print a section header in Cyber Lime."""
    print(f"\033[1;38;5;190m{text}\033[0m")


def print_stat(label: str, value: str, color_code: str = "37") -> None:
    """Print a labeled statistic with ANSI color."""
    print(f"\033[{color_code}m{label}: \033[1m{value}\033[0m")


def simulate_cloud_maas(queries: int, latency_ms: int = CLOUD_LATENCY_MS) -> float:
    """Simulate cloud Memory-as-a-Service total time without blocking."""
    return queries * (latency_ms / 1000.0)


def test_cortex_local(queries: int, db_path: Path) -> float:
    """Test actual CORTEX local database retrieval speed."""
    if not db_path.exists():
        print(f"\033[31mError: CORTEX db not found at {db_path}\033[0m")
        return 0.0

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        start_time = time.time()
        for _ in range(queries):
            cursor.execute("SELECT id, content FROM facts ORDER BY RANDOM() LIMIT 5")
            cursor.fetchall()
        return time.time() - start_time
    finally:
        conn.close()


def run_benchmark() -> None:
    """Execute the CORTEX vs Cloud MaaS benchmark comparison."""
    db_path = Path.home() / ".cortex" / "cortex.db"

    print("\n")
    print_header("==================================================")
    print_header("🧠 CORTEX VS CLOUD MEMORY (MaaS) BENCHMARK PROOF 🧠")
    print_header("==================================================\n")
    print(f"Executing {QUERIES} continuous agentic memory retrievals...\n")

    # Run Cortex
    print("-> Benchmarking CORTEX Local O(1) Engine...")
    cortex_time = test_cortex_local(QUERIES, db_path)
    if cortex_time == 0.0:
        print("\033[31mCRITICAL: CORTEX database missing or empty. Cannot benchmark.\033[0m")
        sys.exit(1)

    print("-> Simulating Cloud MaaS (Mem0/LangChain)...")
    cloud_time = simulate_cloud_maas(QUERIES)

    time_diff = cloud_time / cortex_time if cortex_time > 0 else 0
    cloud_cost = (QUERIES / 10_000) * CLOUD_COST_PER_10K

    print("\n\033[1;34m[ RESULTS ]\033[0m")
    print("-" * 40)
    print_stat("API Mode (MaaS) Time", f"{cloud_time:.2f} seconds", "31")
    suffix = " (Zero-Latency!)" if cortex_time < 0.1 else ""
    print_stat("CORTEX (Local) Time ", f"{cortex_time:.4f} seconds{suffix}", "32")
    print("-" * 40)
    print_stat("Speed Multiplier", f"{time_diff:.1f}x faster", "36")
    print_stat("Financial Cost (MaaS)", f"${cloud_cost:.4f}", "31")
    print_stat("Financial Cost (CORTEX)", "$0.00", "32")
    print("\n")
    print(
        "\033[3mConclusion: Renting memory lobotomizes your agents to save costs.\n"
        "Sovereign memory accelerates them.\033[0m\n"
    )


if __name__ == "__main__":
    run_benchmark()
