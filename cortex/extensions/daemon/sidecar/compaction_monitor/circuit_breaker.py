"""circuit_breaker.py

Compaction Monitor sidecar circuit-breaker.

Delegates to ``cortex.engine.circuit_breaker.CircuitBreaker`` (canonical
implementation). Only the module-level singleton and ``call_external_compact``
helper live here.
"""

import logging
from typing import Any

from cortex.engine.circuit_breaker import CircuitBreaker  # noqa: F401 — re-exported

LOGGER = logging.getLogger(__name__)

# Global instance used by the sidecar runner.
# half_open_success_threshold=2: require 2 consecutive probe successes before closing.
circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    half_open_success_threshold=2,
)


async def call_external_compact(
    engine: Any | None = None,
    project: str = "default",
    db_path: str | None = None,
) -> None:
    """Execute compaction through the circuit breaker.

    Delegates to ``cortex.compaction.compactor.compact`` when available.
    Falls back to a basic WAL checkpoint if the compactor module is unavailable.
    """
    import asyncio

    async def _real_compact():
        try:
            from cortex.compaction.compactor import compact

            if engine is not None:
                # compact() is sync — run in thread to avoid blocking event loop
                return await asyncio.to_thread(compact, engine, project)
        except ImportError:
            pass

        # Fallback: direct SQLite WAL checkpoint
        if db_path:

            def _checkpoint():
                from cortex.database.core import connect as db_connect

                conn = db_connect(db_path, timeout=10)  # type: ignore[reportArgumentType]
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    LOGGER.info("Fallback WAL checkpoint completed for %s", db_path)
                finally:
                    conn.close()

            await asyncio.to_thread(_checkpoint)
        return "ok"

    await circuit_breaker.call(_real_compact)
