#!/usr/bin/env python3
# stress_rag.py
# Mide latencia real y degradación de RAM bajo carga del agente RAG

import subprocess
import time

PYTHON = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
AGENT = "agent_with_tools.py"

QUERIES = [
    "Lista archivos .py en el directorio actual y cuenta cuántos hay.",
    "Muestra git status.",
    "Corre pytest --collect-only.",
    "Lista los últimos 5 commits con git log --oneline.",
    "Muestra el contenido de README.md con bash.",
]


def get_free_ram_mb() -> float:
    result = subprocess.run(["vm_stat"], capture_output=True, text=True)
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
        return {
            "idx": idx,
            "query": query[:40],
            "elapsed_s": 90.0,
            "status": "TIMEOUT",
            "ram_before_mb": ram_before,
            "ram_after_mb": get_free_ram_mb(),
            "ram_delta_mb": 0,
        }


def main():
    print(f"\n{'=' * 60}")
    print("STRESS TEST — Agent RAG Pipeline")
    print(f"Queries: {len(QUERIES)} | Rounds: 3 | Total: {len(QUERIES) * 3}")
    print(f"{'=' * 60}\n")

    results = []
    all_queries = QUERIES * 3

    for i, query in enumerate(all_queries):
        print(f"[{i + 1:02d}/{len(all_queries)}] {query[:40]}...", end=" ", flush=True)
        r = run_query(query, i + 1)
        results.append(r)
        print(f"{r['elapsed_s']}s | RAM delta: -{r.get('ram_delta_mb', 0)} MB | {r['status']}")

        # Parar si RAM cae por debajo de 200 MB
        if r.get("ram_after_mb", 999) < 200:
            print("\n⚠️  RAM CRÍTICA (<200 MB) — deteniendo stress test.")
            break

    # Resumen
    ok = [r for r in results if r["status"] == "OK"]
    times = [r["elapsed_s"] for r in ok]
    ram_deltas = [r["ram_delta_mb"] for r in ok if "ram_delta_mb" in r]

    print(f"\n{'=' * 60}")
    print("RESUMEN")
    print(f"{'=' * 60}")
    print(f"Queries completadas:  {len(ok)}/{len(results)}")
    if times:
        print(f"Latencia media:       {sum(times) / len(times):.2f}s")
        print(f"Latencia mínima:      {min(times):.2f}s")
        print(f"Latencia máxima:      {max(times):.2f}s")
        # Degradación: diferencia entre primera y última latencia
        if len(times) >= 2:
            degradacion = (times[-1] - times[0]) / times[0] * 100
            print(f"Degradación total:    {degradacion:+.1f}%")
    if ram_deltas:
        print(f"RAM consumida total:  {sum(ram_deltas):.1f} MB")
        print(f"RAM delta por query:  {sum(ram_deltas) / len(ram_deltas):.1f} MB")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
