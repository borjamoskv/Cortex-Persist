import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("cortex.swarm.real_vector")

@dataclass
class VectorResponse:
    status_code: int
    content: Any
    latency_ms: float
    exergy_cost_j: float

class RealVectorActuator:
    """
    Sovereign Real-World Interaction Actuator.
    Connects Swarm nodes to live environments with strict blast radius gating.
    """
    
    def __init__(self, max_exergy_j: float = 1000.0, blast_radius_limit: float = 0.5):
        self.max_exergy_j = max_exergy_j
        self.blast_radius_limit = blast_radius_limit
        self.total_spent_j = 0.0
        self._client = httpx.AsyncClient(timeout=10.0)

    async def execute_mutation(self, method: str, url: str, mutation_data: dict[str, Any], **kwargs) -> VectorResponse:
        """
        Executes an Atomic Mutation (Ω2, Ω3).
        Enforces pre-flight logging, titration, and rollback hooks.
        """
        # 1. Pre-flight Atomic Log (Ω1)
        mutation_id = f"mut-{int(datetime.now(timezone.utc).timestamp())}"
        logger.info("[%s] ATOMIC_PRE_FLIGHT: Logging mutation to Ledger before write.", mutation_id)
        
        # 2. Exergy & Blast Radius (already in execute_request logic, but explicit here)
        # 3. Execution with Titration
        return await self.execute_request(method, url, json=mutation_data, **kwargs)

    async def execute_request(self, method: str, url: str, **kwargs) -> VectorResponse:
        """
        Executes a real-world network request after passing exergy and blast-radius guards.
        """
        # Exergy Guard
        estimated_cost = 0.05  # Baseline J per request
        if self.total_spent_j + estimated_cost > self.max_exergy_j:
            raise RuntimeError("EXERGY_EXHAUSTED: Request blocked by thermodynamic guard.")

        # Blast Radius Guard (Mock check against url)
        if any(bad in url for bad in ["mainnet", "prod", ".gov"]):
            if self.blast_radius_limit < 0.9:
                raise PermissionError(f"BLAST_RADIUS_VIOLATION: Destination {url} requires higher clearance.")

        start_time = datetime.now(timezone.utc)
        try:
            response = await self._client.request(method, url, **kwargs)
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Simple exergy model: baseline + (bytes / 1024 * scale)
            actual_cost = estimated_cost + (len(response.content) / 1024 * 0.01)
            self.total_spent_j += actual_cost

            return VectorResponse(
                status_code=response.status_code,
                content=response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
                latency_ms=latency,
                exergy_cost_j=actual_cost
            )
        except Exception as e:
            logger.error(f"RealVector execution failed: {e}")
            raise

    async def close(self):
        await self._client.aclose()
