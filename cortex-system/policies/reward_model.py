"""
C5-REAL: Reward Model & Reinforcement Cycle
Author: Borja Moskv / borjamoskv
"""
from typing import Dict, Any, List, Optional
import asyncio
import time
import json
import logging
from dataclasses import dataclass
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CortexBlackBox")

MUTATION_RATE = 0.05
ORIGINALITY_THRESHOLD = 0.389
DISTRIBUTION_THRESHOLD = 0.161

def reinforcement_cycle(metric: Dict[str, Any], decision: str) -> str:
    """
    Evaluates metric yields to determine the next evolution/adaptation step.

    C5-REAL Patch: "observe" decision maps to "stable" — no rupture on null signal.
    Pressure relief valve: prevents runaway convulsions when swarm has no real data.
    """
    originality_ratio = metric.get('originality_ratio', 1.0)
    distribution_yield = metric.get('distribution_yield', 1.0)
    if decision == 'observe':
        return 'stable'
    if originality_ratio < ORIGINALITY_THRESHOLD:
        return 'force_swarm_mode'
    if distribution_yield < DISTRIBUTION_THRESHOLD:
        return 'inject_attention_pressure'
    if decision == 'default':
        return 'trigger_rupture'
    return 'stable'

# =====================================================================
# BABYLON-60 / CORTEX: Black-Box Benchmark Harness v1.1
# =====================================================================

@dataclass
class EvalMetrics:
    status_code: int
    success: bool
    ttft_seconds: float
    total_latency_seconds: float
    total_tokens: int
    tokens_per_second: float
    error_message: Optional[str] = None

class BlackBoxHarness:
    """
    Empirical observer for chat-completion compliant APIs.
    """
    def __init__(self, api_url: str, api_key: str, model_id: str):
        self.api_url = api_url
        self.api_key = api_key
        self.model_id = model_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def execute_probe(self, prompt: str, parameters: Dict[str, Any]) -> EvalMetrics:
        """
        Executes a single streaming probe to capture exact token issuance latency.
        """
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            **parameters
        }

        start_time = time.perf_counter()
        ttft = -1.0
        total_tokens = 0
        error_message = None
        status_code = 500

        # Use a specific read timeout to prevent hanging on stalled streams
        timeout_config = httpx.Timeout(120.0, read=60.0)

        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                async with client.stream("POST", self.api_url, headers=self.headers, json=payload) as response:
                    status_code = response.status_code
                    if status_code != 200:
                        error_body = await response.aread()
                        # Truncate error body to prevent log spam/sensitive data leaks
                        raise httpx.HTTPStatusError(
                            f"HTTP {status_code}: {error_body.decode(errors='ignore')[:100]}", 
                            request=response.request, 
                            response=response
                        )

                    async for line in response.iter_lines():
                        if not line.strip() or line == "data: [DONE]":
                            continue
                        
                        if line.startswith("data: "):
                            # Capture TTFT strictly on the first token payload
                            if ttft < 0:
                                ttft = time.perf_counter() - start_time
                            
                            try:
                                data_json = json.loads(line[6:])
                                choices = data_json.get("choices", [])
                                if choices and "content" in choices[0].get("delta", {}):
                                    total_tokens += 1
                            except json.JSONDecodeError:
                                pass

        except asyncio.TimeoutError:
            error_message = "Stream read timeout exceeded (stalled connection)."
            logger.error(f"Probe execution failed: {error_message}")
        except Exception as e:
            error_message = str(e)
            logger.error(f"Probe execution failed: {error_message}")

        total_latency = time.perf_counter() - start_time
        
        # FIX 1: Safe throughput calculation preventing division by zero or negative time
        generation_time = (total_latency - ttft) if ttft > 0 else total_latency
        tps = total_tokens / max(generation_time, 1e-6) 

        return EvalMetrics(
            status_code=status_code,
            success=error_message is None and status_code == 200,
            ttft_seconds=ttft,
            total_latency_seconds=total_latency,
            total_tokens=total_tokens,
            tokens_per_second=tps,
            error_message=error_message
        )

    async def evaluate_suite(self, prompts: List[str], parameters: Dict[str, Any], concurrency: int = 2) -> List[EvalMetrics]:
        """
        Executes a bounded concurrent evaluation of multiple prompts.
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_probe(p: str) -> EvalMetrics:
            async with semaphore:
                return await self.execute_probe(p, parameters)

        tasks = [bounded_probe(p) for p in prompts]
        return await asyncio.gather(*tasks)

# =====================================================================
# INTEGRATION BINDING FOR: cortex/engine/reward_model.py
# =====================================================================
async def cortex_empirical_reward_binding(
    prompts: List[str], 
    api_key: str, 
    model_id: str,
    api_url: str = "https://api.openai.com/v1/chat/completions", # FIX 2: Configurable URL
    tps_normalization_factor: float = 100.0                      # FIX 3: Configurable normalization
) -> float:
    """
    Provides a deterministic scalar reward signal based on verifiable black-box behavior.
    """
    harness = BlackBoxHarness(
        api_url=api_url,
        api_key=api_key,
        model_id=model_id
    )
    
    # Enforce deterministic constraints for evaluation (T=0.0)
    results = await harness.evaluate_suite(prompts, {"temperature": 0.0})
    
    successful_runs = [r for r in results if r.success]
    if not successful_runs:
        return 0.0
        
    avg_tps = sum(r.tokens_per_second for r in successful_runs) / len(successful_runs)
    success_rate = len(successful_runs) / len(results)
    
    # Simplified Exergy/Reward calculation based strictly on observables
    reward_score = success_rate * (avg_tps / tps_normalization_factor) 
    
    logger.info(f"Empirical Reward Resolved: {reward_score:.4f} (Success: {success_rate*100}%, TPS: {avg_tps:.2f})")
    return min(reward_score, 1.0)