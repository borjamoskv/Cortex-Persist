"""legion_integration.py

Integration with the LEGION swarm to offload specialist components of the
Compaction Monitor sidecar. This module provides a thin wrapper around the
LEGION client (if available) and registers the ``compaction_job`` as a task
that can be executed by specialist agents.

In a full MOSKV‑1 environment the ``legion`` package offers an async API:
```
from legion import LegionClient
```
For the purpose of this repository we provide a minimal stub that can be
replaced with the real client when the swarm is deployed.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

LOGGER = logging.getLogger(__name__)


# Stub client – in production this would be the real LEGION client.
class _StubLegionClient:
    def __init__(self, address: str = "localhost", port: int = 8000):
        self.address = address
        self.port = port
        LOGGER.info("Initialized stub LEGION client at %s:%d", address, port)

    async def submit_task(self, name: str, payload: dict) -> str:
        """Simulate submitting a task to the swarm.

        Returns a task identifier.
        """
        await asyncio.sleep(0.1)  # simulate network latency
        task_id = f"legion-{name}-{int(asyncio.get_event_loop().time())}"
        LOGGER.info("Submitted LEGION task %s with payload %s", task_id, payload)
        return task_id

    async def get_result(self, task_id: str) -> Any:
        """Simulate retrieving a result – always succeeds after a short delay."""
        await asyncio.sleep(0.2)
        LOGGER.info("Retrieved result for LEGION task %s", task_id)
        return {"status": "success"}


# Global client instance – can be replaced by real client via env var.
legion_client = _StubLegionClient()


async def dispatch_compaction_via_legion(compaction_callback: Callable[[Any], Any]) -> None:
    """Dispatch the compaction job to a specialist LEGION agent.

    The ``compaction_callback`` is the same callable used by the local runner.
    This function packages the request and sends it to the swarm. When the
    result arrives it invokes the callback locally.
    """
    payload = {"action": "compaction", "timestamp": asyncio.get_event_loop().time()}
    task_id = await legion_client.submit_task("compaction_job", payload)
    result = await legion_client.get_result(task_id)
    if result.get("status") == "success":
        # Directly call the local compaction logic – in a real system the
        # agent would perform the work and return detailed stats.
        await compaction_callback(None)
    else:
        LOGGER.error("LEGION compaction task %s failed: %s", task_id, result)
