#!/usr/bin/env python3
# stress_rag.py
# Measures real latency and RAM degradation under RAG agent load

import subprocess
import time

PYTHON = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
AGENT  = "agent_with_tools.py"

QUERIES = [
    "List .py files in current directory and count them.",
    "Show git status.",
    "Run pytest --collect-only.",
    "List the last 5 commits with git log --oneline.",
    "Show the content of README.md with bash.",
]

def get_free_ram_mb() -> float:
    result = subprocess.run(
        ["vm_stat"], capture_output=True, text=True
    )
    pages_free = 0
    for line in result.stdout.splitlines():
        if "Pages free" in line:
            pages_free = int(line.split(":")[1].strip().rstrip("."))
            break
    return (pages_free * 16384) / (1024 * 1024)  # MB

def run_query(query: str, idx: int) -> dict:
    ram_before = get_free_ram_mb()
    start = time.time()
    try:
        result = subprocess.run(
            [PYTHON, AGENT],
            input=query + "\nq\n",
            capture_output=True,
            text=True,
            timeout=90,
        )
        elapsed = time.time() - start
        ram_after = get_free_ram_mb()
        return {
            "idx": idx,
            "query": query[:40],
            "elapsed_s": round(elapsed, 2),
            "ram_before_mb": round(ram_before, 1),
            "ram_after_mb": round(ram_after, 1),
            "ram_delta_mb": round(ram_before - ram_after, 1),
            "status": "OK" if result.returncode == 0 else f"ERR({result.returncode})",
        }
    except subprocess.TimeoutExpired:
        return {"idx": idx, "query": query[:40], "elapsed_s": 90.0,
                "status": "TIMEOUT", "ram_before_mb": ram_before,
                "ram_after_mb": get_free_ram_mb(), "ram_delta_mb": 0}

def main():
    print(f"\n{'='*60}")
    print("STRESS TEST — Agent RAG Pipeline")
    print(f"Queries: {len(QUERIES)} | Rounds: 3 | Total: {len(QUERIES)*3}")
    print(f"{'='*60}\n")

    results = []
    all_queries = QUERIES * 3

    for i, query in enumerate(all_queries):
        print(f"[{i+1:02d}/{len(all_queries)}] {query[:40]}...", end=" ", flush=True)
        r = run_query(query, i + 1)
        results.append(r)
        print(f"{r['elapsed_s']}s | RAM delta: -{r.get('ram_delta_mb', 0)} MB | {r['status']}")

        # Stop if RAM falls below 200 MB
        if r.get("ram_after_mb", 999) < 200:
            print("\n⚠️  CRITICAL RAM (<200 MB) — stopping stress test.")
            break

    # Summary
    ok = [r for r in results if r["status"] == "OK"]
    times = [r["elapsed_s"] for r in ok]
    ram_deltas = [r["ram_delta_mb"] for r in ok if "ram_delta_mb" in r]

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Completed queries:    {len(ok)}/{len(results)}")
    if times:
        print(f"Average latency:      {sum(times)/len(times):.2f}s")
        print(f"Minimum latency:      {min(times):.2f}s")
        print(f"Maximum latency:      {max(times):.2f}s")
        # Degradation: difference between first and last latency
        if len(times) >= 2:
            degradation = (times[-1] - times[0]) / times[0] * 100
            print(f"Total degradation:    {degradation:+.1f}%")
    if ram_deltas:
        print(f"Total RAM consumed:   {sum(ram_deltas):.1f} MB")
        print(f"RAM delta per query:  {sum(ram_deltas)/len(ram_deltas):.1f} MB")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
