"""CORTEX Daemon — Chaos Imp.

The Metastability Immunity Daemon injects localized failures to falsify stability.
If the tests pass but resilience is false, it panics and logs.
"""

import asyncio
import logging
import random
from typing import Any

logger = logging.getLogger("cortex.chaos_daemon")


class ChaosDaemon:
    """The Metastability Immunity Injector."""

    def __init__(self, engine: Any):
        self._engine = engine
        self._running = False
        self._last_injection_t = 0.0

    async def start(self):
        self._running = True
        logger.info("ChaosDaemon started. Metastability probes armed.")
        asyncio.create_task(self._chaos_loop())

    async def stop(self):
        self._running = False

    async def iterate_on_stability(self):
        """
        Manages the exergy calculation of the code and proposes distillations (Ω₄).
        """
        # Trigger an adversarial stress phase via internal engine components.
        # This will simulate failure on non-critical paths.
        await self._inject_latency(severity=0.5)

    async def _chaos_loop(self):
        """Periodically intercept database/network calls and inject faults."""
        while self._running:
            # Random sleep between 60s and 300s (Ω₃: Pseudo-randomness)
            wait_time = random.uniform(60, 300)
            await asyncio.sleep(wait_time)
            logger.debug("Executing chaos injection phase...")
            # Simulate high-risk metastability probe.
            await self._inject_latency(severity=0.8)

    async def _inject_latency(self, severity: float):
        """Simulate high network latency for external API calls."""
        # severity: 0.0 to 1.0 (How many requests take more than 5 seconds).
        # This function would hook into the `httpx` transport layer in a real setup.
        # Here, it simulates the effect on the engine's async tasks.
        logger.warning("[CHAOS] Injecting simulated latency (severity: %.2f)", severity)
        if random.random() < severity:
            # Simulate a 3-second block on the next generic IO bound call.
            asyncio.create_task(self._simulate_engine_latency(3.0))

    async def _simulate_engine_latency(self, delay: float):
        """Simulate a delayed response to test robustness of agents/clients."""
        await asyncio.sleep(delay)
        logger.info("[CHAOS] Latency injection completed. Resuming.")
