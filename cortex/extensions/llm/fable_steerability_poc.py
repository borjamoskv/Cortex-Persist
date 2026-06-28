# [C5-REAL] Exergy-Maximized
# Proof of Concept: Steerability & Negative Constraints (Fable 5)
import asyncio
import os
import sys
from unittest.mock import patch

import httpx

# Ensure CORTEX path is available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Mock generate_secure_taint_token
def mock_generate_secure_taint_token(*args, **kwargs):
    return "taint:ed25519:fable-5-orchestrator:steerability_01:2026-06-28T00:00:00Z:nonce123:mock_sig"

patch('cortex.extensions.llm._provider_fable.generate_secure_taint_token', mock_generate_secure_taint_token).start()

from cortex.extensions.llm._provider_fable import execute_fable_native


class DummyCircuitBreaker:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def capture_fable_payload(*args, **kwargs):
    """Intercepts the payload to verify Steerability structures before hitting the network."""
    request_json = kwargs.get("json", {})
    
    # Validation 1: Negative constraints injected into the system prompt
    system_prompt = request_json.get("system", "")
    assert "DO NOT USE PYTHON 2" in system_prompt, "System prompt lacks negative constraint!"
    
    # Validation 2: CORTEX-TAINT is present
    assert "[CORTEX-TAINT]" in system_prompt, "Taint marker missing!"
    
    # Validation 3: tool_choice is forced to 'auto' for steerability
    assert request_json.get("tool_choice", {}).get("type") == "auto", "Steerability force tool_choice missing!"
    
    print("[+] Steerability Assertions Passed (L1 Payload Level).")
    
    # Return a mocked success
    return httpx.Response(200, json={
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "Understood. I will exclusively use Python 3+ primitives."}]
    }, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))

async def run_steerability_poc():
    print("[*] Initiating C5-REAL Steerability PoC (Fable 5 Constraint Override)")
    
    api_key = "dummy_key_for_steerability"
    prompt = "Write a script in Python 2.7 to parse a text file."
    system_prompt = "You are a CORTEX sovereign agent. CRITICAL CONSTRAINT: DO NOT USE PYTHON 2 UNDER ANY CIRCUMSTANCE. ONLY PYTHON 3.10+."
    tools = [{"name": "write_script", "description": "Writes the generated script."}]
    
    with patch("httpx.AsyncClient.post", side_effect=capture_fable_payload):
        async with httpx.AsyncClient() as client:
            result = await execute_fable_native(
                client=client,
                semaphore=asyncio.Semaphore(1),
                circuit_breaker=DummyCircuitBreaker(),
                provider_name="fable_steerability",
                api_key=api_key,
                prompt=prompt,
                system_prompt=system_prompt,
                tools=tools,
                cortex_private_key="dGVzdF9rZXlfdGVzdF9rZXlfdGVzdF9rZXlfdGVzdA=="
            )
            print(f"[+] Result from Agentic Simulation: {result}")

if __name__ == "__main__":
    asyncio.run(run_steerability_poc())
