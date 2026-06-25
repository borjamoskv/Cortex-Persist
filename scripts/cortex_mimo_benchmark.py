"""
CORTEX-Persist - MiMo-V2.5-Pro Swarm Benchmarking (C5-REAL)
Validates latency and throughput (Information Exergy dynamics) of the vLLM local deployment.
Calculates times, TTFT, and TPS using BABYLON-60 Epistemology.
"""
import argparse
import asyncio
import time
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

import httpx
from cortex.engine.cortex import Cortex


async def fetch_completion(client: httpx.AsyncClient, url: str, payload: dict, agent_id: int) -> dict:
    start_time = time.perf_counter()
    ttft = Cortex(0.0)
    token_count = 0
    ttft_set = False
    
    try:
        async with client.stream("POST", url, json=payload, timeout=120.0) as response:
            response.raise_for_status()
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    data_str = chunk[6:]
                    if data_str == "[DONE]":
                        break
                    if not ttft_set:
                        ttft = Cortex(time.perf_counter() - start_time)
                        ttft_set = True
                    # Approximate token count for continuous batching telemetry
                    token_count += 1
    except Exception as e:
        print(f"[Agent-{agent_id}] Evaluation Error: {e}")

    total_time = Cortex(time.perf_counter() - start_time)
    tps = Cortex(token_count) / total_time if total_time > 0.0 else Cortex(0.0)
    
    return {
        "agent_id": agent_id,
        "ttft": ttft,
        "total_time": total_time,
        "tokens": token_count,
        "tps": tps
    }

async def run_swarm_benchmark(url: str, concurrency: int, prompt_len: int, max_tokens: int):
    # Constructing a dummy AST projection skeleton
    dummy_prompt = "class CortexSwarmAgent:\n" + "    def execute(self):\n        pass\n" * prompt_len
    
    payload = {
        "model": "XiaomiMiMo/MiMo-V2.5-Pro",
        "prompt": dummy_prompt,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": True
    }

    print("=== [C5-REAL] SWARM BENCHMARK START ===")
    print(f"vLLM Target: {url}")
    print(f"Concurrency: {concurrency} agents | AST Context Skeleton Size: {len(dummy_prompt)} chars")

    start_swarm = time.perf_counter()
    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_completion(client, url, payload, i)
            for i in range(concurrency)
        ]
        results = await asyncio.gather(*tasks)
    
    total_time = Cortex(time.perf_counter() - start_swarm)
    total_tokens = sum(r["tokens"] for r in results)
    
    sum_ttft = Cortex(0.0)
    for r in results:
        sum_ttft += r["ttft"]
    avg_ttft = sum_ttft / Cortex(concurrency) if concurrency > 0 else Cortex(0.0)
    
    throughput = Cortex(total_tokens) / total_time if total_time > 0.0 else Cortex(0.0)
    
    print("\n=== THERMODYNAMIC METRICS: LATENCY & THROUGHPUT (BABYLON-60) ===")
    print(f"Total Wall-clock Time: {total_time.to_float():.2f}s")
    print(f"Total Verifiable Tokens Generated: {total_tokens}")
    print(f"Swarm Throughput (Exergy Extraction Rate): {throughput.to_float():.2f} tokens/sec")
    print(f"Average TTFT (Time-To-First-Token): {avg_ttft.to_float():.4f}s")
    
    print("\n[Sample Agents Telemetry]")
    for r in results[:5]:
        print(f"  Agent-{r['agent_id']:03d}: TTFT={r['ttft'].to_float():.4f}s | TPS={r['tps'].to_float():.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="[C5-REAL] MiMo-V2.5-Pro vLLM Swarm Benchmark")
    parser.add_argument("--url", default="http://localhost:8000/v1/completions", help="vLLM completions endpoint")
    parser.add_argument("--concurrency", type=int, default=128, help="Number of concurrent swarm agents")
    parser.add_argument("--prompt-len", type=int, default=500, help="AST skeleton multiplier (simulates context length)")
    parser.add_argument("--max-tokens", type=int, default=256, help="Tokens to generate per agent")
    args = parser.parse_args()

    asyncio.run(run_swarm_benchmark(args.url, args.concurrency, args.prompt_len, args.max_tokens))

