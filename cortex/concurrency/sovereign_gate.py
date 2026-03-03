"""cortex.concurrency.sovereign_gate — Centralized Throttling Layer.

Governs all outgoing HTTP traffic to prevent Thundering Herd.
Combines a local process-level Semaphore with a distributed Token Bucket (SQLite WAL).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from cortex.llm.quota import SovereignQuotaManager

logger = logging.getLogger("cortex.concurrency.gate")

_DEFAULT_MAX_CONCURRENT: Final[int] = 50


class SovereignGate:
    """Singleton governing outgoing concurrency via Local Semaphore + Distributed Quota."""

    _instance: SovereignGate | None = None

    def __init__(self, max_concurrent: int = _DEFAULT_MAX_CONCURRENT):
        if SovereignGate._instance is not None:
            raise RuntimeError("SovereignGate is a singleton. Use SovereignGate.shared()")

        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Lazy import to avoid circular dependencies
        from cortex.llm.quota import SovereignQuotaManager
        self._quota = SovereignQuotaManager()

        SovereignGate._instance = self
        logger.debug("SovereignGate initialized (max_local=%d)", max_concurrent)

    @classmethod
    def shared(cls) -> SovereignGate:
        """Access the shared gate instance."""
        if cls._instance is None:
            cls._instance = SovereignGate()
        return cls._instance

    @asynccontextmanager
    async def gate(self, provider: str = "default", tokens: int = 1, deadline: float = 120.0):
        """Asynchronous context manager to throttle execution."""
        async with self._semaphore:
            success = await self._quota.acquire(provider=provider, tokens=tokens, deadline=deadline)
            if not success:
                from cortex.utils.errors import CortexError
                raise CortexError(f"Gate Timeout: Could not acquire quota for {provider}")
            yield
