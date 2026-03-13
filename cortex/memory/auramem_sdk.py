"""
CORTEX v7 — AuraMem Python SDK
Sovereign 130/100 Protocol

Zero-drift Semantic RAM Client. Connects to the AuraMem edge API
to provide O(1) deduplication before facts ever hit the local vector store.
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger("cortex.auramem_sdk")


class AuraMemClient:
    """
    Sovereign SDK for AuraMem.
    Requires AURAMEM_API_KEY to be set in the environment or passed during initialization.
    """

    def __init__(self, api_key: str | None = None, base_url: str = "http://localhost:3000/api/v1"):
        self.api_key = api_key or os.environ.get("AURAMEM_API_KEY")
        if not self.api_key:
            logger.warning(
                "AURA-MEM: No API key provided. Operating in detached mode (will fail if used)."
            )

        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def store(
        self, agent_id: str, fact: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Submits a fact to AuraMem for O(1) deduplication and storage.

        Returns a dict containing:
        - status: 'stored' or 'deduplicated'
        - message: Contextual message
        - memory_count: Total memories for agent
        """
        if not self.api_key:
            raise ValueError("AURAMEM_API_KEY is required to invoke AuraMem")

        payload = {"agent_id": agent_id, "fact": fact, "metadata": metadata or {}}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.post(f"{self.base_url}/memory", json=payload) as response:
                    if response.status == 401:
                        logger.error("AURA-MEM: Unauthorized. Invalid API Key.")
                        response.raise_for_status()

                    data = await response.json()

                    if data.get("status") == "deduplicated":
                        logger.info(
                            "AURA-MEM ⚡: Semantic deduplication triggered for agent %s. Fact ignored.",
                            agent_id,
                        )
                    else:
                        logger.info("AURA-MEM ✓: New fact stored for agent %s.", agent_id)

                    return data
            except aiohttp.ClientError as e:
                logger.error("AURA-MEM ❌: Edge submission failed - %s", e)
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("AURA-MEM ❌: Edge submission unexpected error - %s", e)
                from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

                ErrorGhostPipeline().capture_sync(
                    e, source="auramem:store", project="CORTEX_SYSTEM"
                )
                raise

    async def recall(self, agent_id: str, query: str) -> dict[str, Any]:
        """
        Retrieves context from AuraMem.
        """
        if not self.api_key:
            raise ValueError("AURAMEM_API_KEY is required to invoke AuraMem")

        params = {"agent_id": agent_id, "query": query}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(f"{self.base_url}/memory", params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    # Mock metric logging
                    saved = data.get("context_tokens_saved", 0)
                    if saved > 0:
                        logger.info("AURA-MEM: Edge retrieval saved %s tokens of noise.", saved)
                    return data
            except aiohttp.ClientError as e:
                logger.error("AURA-MEM ❌: Edge recall failed - %s", e)
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("AURA-MEM ❌: Edge recall unexpected error - %s", e)
                from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

                ErrorGhostPipeline().capture_sync(
                    e, source="auramem:recall", project="CORTEX_SYSTEM"
                )
                raise


# Global singleton for CORTEX use
auramem = AuraMemClient()
