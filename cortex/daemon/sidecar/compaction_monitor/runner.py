"""runner.py

Async entry point for the Compaction Monitor sidecar.
It sets up uvloop, connects to Redis (ARQ), starts the pressure watcher
and registers the compaction job handler.
"""

import asyncio
import logging
import os
import signal
from typing import Any

# uvloop for high‑performance event loop
try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    logging.warning("uvloop not installed; falling back to default asyncio loop")

# ARQ (async Redis queue) – optional, fallback to in‑process queue if Redis unavailable
try:
    from arq import Queue, Worker, create_pool
    from arq.connections import RedisSettings
except ImportError:
    RedisSettings = None
    Queue = None
    Worker = None
    logging.warning("arq not installed; sidecar will use a dummy in‑process queue")

# Local imports
from .circuit_breaker import circuit_breaker
from .memory_wrapper import get_mallinfo2, malloc_trim
from .pressure_watcher import start_pressure_watcher

LOGGER = logging.getLogger("compaction_sidecar")
logging.basicConfig(level=logging.INFO)


async def compaction_job(ctx: Any) -> None:
    """Job executed when memory pressure is high.

    It collects detailed arena stats, attempts to trim the heap and logs the outcome.
    The external Cortex compactor service is called through the circuit breaker.
    """
    try:
        info = get_mallinfo2()
        LOGGER.info("MallInfo2 before trim: %s", info)
        # Attempt to release memory back to OS
        malloc_trim()
        info_after = get_mallinfo2()
        LOGGER.info("MallInfo2 after trim: %s", info_after)
        # Call external compaction service (placeholder)
        await circuit_breaker.call_external_compact()
    except Exception as exc:
        LOGGER.exception("Compaction job failed: %s", exc)


async def shutdown(signal, loop):
    """Cleanup tasks on termination signals."""
    LOGGER.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main() -> None:
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    # Start pressure watcher (runs in background)
    watcher_task = asyncio.create_task(start_pressure_watcher(compaction_job))

    # Set up ARQ worker if available
    if RedisSettings is not None:
        redis = RedisSettings(
            host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379"))
        )

        # Register the job
        async def startup(ctx):
            ctx["queue"] = await create_pool(redis)

        worker = Worker([compaction_job], redis_settings=redis, on_startup=startup)
        worker_task = asyncio.create_task(worker.run())
        await asyncio.gather(watcher_task, worker_task)
    else:
        # Fallback: run watcher only; it will invoke compaction_job directly
        await watcher_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
