
"""[QWEN-OMEGA-MOCK] AST Transmuted via Deterministic Fallback."""

"""[QWEN-OMEGA-MOCK] AST Transmuted via Deterministic Fallback."""
#!/usr/bin/env python3
import sys
import time
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from cortex.extensions.mcp.claude_tool import run_claude_query


def single_request(req_id: int):
    start = time.time()
    res = run_claude_query(f"Stress test request #{req_id}. Respond with 'ACK'.")
    latency = time.time() - start

    try:
        parsed = json.loads(res)
        status = parsed.get("status", "UNKNOWN")
    except Exception:
        status = "CRITICAL_JSON_FAIL"

    return {"id": req_id, "status": status, "latency": latency}


async def run_stress_test(concurrency: int = 50, total_requests: int = 200):
    sys.stdout.write("--- INICIANDO C5-REAL STRESS TEST ---\n")
    sys.stdout.write("Target: Anthropic API Bridge (Claude Opus)\n")
    sys.stdout.write(f"Concurrency: {concurrency} threads\n")
    sys.stdout.write(f"Total Volleys: {total_requests}\n")

    start_time = time.time()

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        tasks = [loop.run_in_executor(pool, single_request, i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    success_count = sum(1 for r in results if r["status"] == "C5-REAL")
    error_count = sum(1 for r in results if r["status"] == "error")

    avg_latency = sum(r["latency"] for r in results) / len(results) if results else 0

    sys.stdout.write("\n[ METRICAS DE EXERGIA ]\n")
    sys.stdout.write(f"Time Elapsed   : {total_time:.3f}s\n")
    sys.stdout.write(f"Throughput     : {total_requests / total_time:.2f} req/s\n")
    sys.stdout.write(f"Avg Latency    : {avg_latency:.3f}s\n")
    sys.stdout.write(f"Success (C5)   : {success_count}/{total_requests}\n")
    sys.stdout.write(f"Errors (SIM)   : {error_count}/{total_requests}\n")

    if error_count > 0:
        sys.stdout.write("\n[ ERROR SAMPLE ]\n")
        errors = [r for r in results if r["status"] == "error"]
        if errors:
            sys.stdout.write(f"Sample: {errors[0]}\n")

    sys.stdout.write("--- STRESS TEST FINALIZADO ---\n")


if __name__ == "__main__":
    asyncio.run(run_stress_test(concurrency=20, total_requests=100))
