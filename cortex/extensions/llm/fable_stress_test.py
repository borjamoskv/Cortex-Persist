# [C5-REAL] Exergy-Maximized
# Asynchronous Stress Test: Claude Fable 5 Agentic Orchestrator
import asyncio
import os
import sys
import time
from unittest.mock import patch

import httpx

# Ensure CORTEX path is available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Mock generate_secure_taint_token to bypass crypto keys for PoC
def mock_generate_secure_taint_token(*args, **kwargs):
    return "taint:ed25519:fable-5-orchestrator:stress_harness:2026-06-28T00:00:00Z:nonce123:mock_sig"

patch('cortex.extensions.llm._provider_fable.generate_secure_taint_token', mock_generate_secure_taint_token).start()

from cortex.extensions.llm._provider_fable import execute_fable_native


class DummyCircuitBreaker:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def simulate_fable_api_response(*args, **kwargs):
    """Simulate Fable 5 API latency and agentic tool call response."""
    await asyncio.sleep(0.05)  # 50ms simulated network latency
    mock_resp = httpx.Response(
        200,
        json={
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_01",
                    "name": "read_cortex_ledger",
                    "input": {"limit": 10}
                }
            ]
        },
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    return mock_resp

async def stress_worker(client: httpx.AsyncClient, worker_id: int, semaphore: asyncio.Semaphore):
    api_key = "dummy_key_for_stress"
    prompt = f"Worker {worker_id} - Verify CORTEX ledger."
    system_prompt = "You are an autonomous auditor."
    tools = [{"name": "read_cortex_ledger", "description": "Reads ledger."}]
    
    start_time = time.perf_counter()
    try:
        result = await execute_fable_native(
            client=client,
            semaphore=semaphore,
            circuit_breaker=DummyCircuitBreaker(),
            provider_name=f"fable_stress_{worker_id}",
            api_key=api_key,
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tools,
            cortex_private_key="dGVzdF9rZXlfdGVzdF9rZXlfdGVzdF9rZXlfdGVzdA=="
        )
        latency = time.perf_counter() - start_time
        return {"id": worker_id, "status": "success", "latency": latency, "result": result}
    except Exception as e:
        latency = time.perf_counter() - start_time
        return {"id": worker_id, "status": "error", "latency": latency, "error": str(e)}

async def run_stress_test(concurrency: int, total_requests: int):
    print(f"[*] Initiating C5-REAL Async Stress Test: {total_requests} requests (Concurrency limit: {concurrency})")
    
    semaphore = asyncio.Semaphore(concurrency)
    
    # Patch httpx.AsyncClient.post to intercept the API call
    with patch("httpx.AsyncClient.post", side_effect=simulate_fable_api_response):
        async with httpx.AsyncClient() as client:
            tasks = [stress_worker(client, i, semaphore) for i in range(total_requests)]
            start_wall = time.perf_counter()
            
            results = await asyncio.gather(*tasks)
            
            total_wall_time = time.perf_counter() - start_wall
            
    successes = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]
    
    avg_latency = sum(r["latency"] for r in successes) / len(successes) if successes else 0
    
    print("\n=== [CORTEX] STRESS TEST RESULTS ===")
    print(f"Total Requests: {total_requests}")
    print(f"Concurrency Limit: {concurrency}")
    print(f"Wall Time: {total_wall_time:.3f}s")
    print(f"Successful: {len(successes)}")
    print(f"Failed: {len(errors)}")
    if successes:
        print(f"Average Latency per task: {avg_latency:.3f}s")
    if errors:
        print(f"Sample Error: {errors[0]['error']}")

if __name__ == "__main__":
    # Invocamos 100 tareas asíncronas concurrentes, limitadas por un semáforo de 20
    asyncio.run(run_stress_test(concurrency=20, total_requests=100))
