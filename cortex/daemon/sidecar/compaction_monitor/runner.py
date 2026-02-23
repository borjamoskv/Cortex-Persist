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
from .monitor import MemoryPressureMonitor

LOGGER = logging.getLogger("compaction_sidecar")
logging.basicConfig(level=logging.INFO)


async def compaction_job(ctx: Any = None) -> None:
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


async def shutdown(sig, loop, monitor: MemoryPressureMonitor | None = None):
    """Cleanup tasks on termination signals."""
    LOGGER.info(f"Received exit signal {sig.name}...")
    if monitor:
        await monitor.stop()

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main() -> None:
    loop = asyncio.get_running_loop()

    # Initialize Monitor (Nivel 130/100)
    monitor = MemoryPressureMonitor(
        interval=int(os.getenv("PSI_WATCH_INTERVAL", "5")),
        # Use a safe default for sys_free_threshold (e.g. 15% free)
        sys_free_threshold=float(os.getenv("PSI_PRESSURE_THRESHOLD", "15")) / 100.0,
        alert_callback=lambda alert: compaction_job(None),
        use_legion=True,
    )

    # State for cleanup
    arq_pool = None

    async def _shutdown_handler(sig):
        """Internal helper to bridge signal to shutdown."""
        nonlocal arq_pool
        if arq_pool:
            await arq_pool.close()
        await shutdown(sig, loop, monitor)

    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(_shutdown_handler(s)))

    # Start the monitor
    monitor.start(loop=loop)

    # Set up ARQ worker if available
    if RedisSettings is not None:
        redis_settings = RedisSettings(
            host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379"))
        )

        # Register the job
        async def on_startup(ctx):
            nonlocal arq_pool
            arq_pool = await create_pool(redis_settings)
            ctx["queue"] = arq_pool
            LOGGER.info("ARQ Worker initialized with Redis pool.")

        async def on_shutdown(ctx):
            LOGGER.info("ARQ Worker shutting down...")
            if "queue" in ctx:
                await ctx["queue"].close()

        worker = Worker(
            functions=[compaction_job],
            redis_settings=redis_settings,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        )
        try:
            await worker.run()
        except asyncio.CancelledError:
            LOGGER.info("Worker execution cancelled.")
            raise
    else:
        # Fallback: keep the loop alive since monitor runs as a background task
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            LOGGER.info("Main loop cancelled.")
            await monitor.stop()
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
